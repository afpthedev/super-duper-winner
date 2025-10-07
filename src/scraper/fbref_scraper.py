import logging
import re
import time
import warnings
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

warnings.simplefilter(action='ignore', category=FutureWarning)

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FBRefScraper:
    """
    FBRef sitesinden futbolcu verilerini çekmek için scraper sınıfı.
    Makaledeki yaklaşımı temel alarak geliştirilmiştir.
    """

    SQUAD_TABLE_ID_PREFIX = "stats_standard"
    COLUMN_RENAMES: Dict[str, str] = {
        "Player": "player_name",
        "Pos": "position",
        "Nation": "nationality",
        "Age": "age",
        "Born": "birth_year",
        "MP": "matches_played",
        "Starts": "starts",
        "Min": "minutes_played",
        "90s": "minutes_90s",
        "Gls": "goals",
        "Ast": "assists",
        "G+A": "goals_plus_assists",
        "G-PK": "non_penalty_goals",
        "G+A-PK": "non_penalty_goals_plus_assists",
        "PK": "penalties_scored",
        "PKatt": "penalties_attempted",
        "CrdY": "yellow_cards",
        "CrdR": "red_cards",
        "xG": "expected_goals",
        "npxG": "non_penalty_expected_goals",
        "xAG": "expected_assists",
        "npxG+xAG": "expected_goals_plus_assists",
        "PrgC": "progressive_carries",
        "PrgP": "progressive_passes",
        "PrgR": "progressive_passes_received",
    }
    INTEGER_COLUMNS: List[str] = [
        "matches_played",
        "starts",
        "minutes_played",
        "goals",
        "assists",
        "goals_plus_assists",
        "non_penalty_goals",
        "non_penalty_goals_plus_assists",
        "penalties_scored",
        "penalties_attempted",
        "yellow_cards",
        "red_cards",
        "progressive_carries",
        "progressive_passes",
        "progressive_passes_received",
    ]
    FLOAT_COLUMNS: List[str] = [
        "expected_goals",
        "expected_assists",
        "non_penalty_expected_goals",
        "expected_goals_plus_assists",
        "minutes_90s",
    ]
    INVALID_PLAYER_NAMES = {"squad total", "squad total 2", "opponent total", "opponent", "matches"}
    
    def __init__(self, headless: bool = True, delay: float = 2.0):
        """
        Scraper'ı başlatır.
        
        Args:
            headless: Tarayıcıyı görünmez modda çalıştır
            delay: İstekler arasındaki bekleme süresi (saniye)
        """
        self.headless = headless
        self.delay = delay
        self.driver = None
        self.session = requests.Session()
        
        # User-Agent ayarla
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def setup_driver(self):
        """Selenium WebDriver'ı ayarlar."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def close_driver(self):
        """WebDriver'ı kapatır."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    @staticmethod
    def _clean_column_names(columns: Iterable) -> List[str]:
        """FBRef tablolarındaki çok seviyeli kolon adlarını sadeleştirir."""
        cleaned_columns: List[str] = []
        seen: Dict[str, int] = {}

        for column in columns:
            if isinstance(column, tuple):
                parts = [
                    str(part).strip()
                    for part in column
                    if part and not str(part).startswith("Unnamed")
                ]
                name = parts[-1] if parts else str(column[-1]).strip()
            else:
                name = str(column).strip()

            if not name:
                name = f"column_{len(cleaned_columns)}"

            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0

            cleaned_columns.append(name)

        return cleaned_columns

    @staticmethod
    def _clean_player_name(name: Any) -> str:
        if pd.isna(name):
            return ""
        cleaned = str(name).strip()
        if not cleaned:
            return ""
        cleaned = cleaned.replace("\xa0", " ")
        cleaned = re.sub(r"[+*]+", "", cleaned)
        return cleaned

    @staticmethod
    def _parse_age(value: Any) -> Optional[int]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        if not text:
            return None
        if "-" in text:
            text = text.split("-")[0]
        if not text:
            return None
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalise_squad_dataframe(cls, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Kadro tablosunu temizler ve standart kolon adlarına dönüştürür."""
        df = dataframe.copy()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = cls._clean_column_names(df.columns.tolist())

        df = df.loc[:, ~df.columns.duplicated()]

        rename_map = {original: renamed for original, renamed in cls.COLUMN_RENAMES.items() if original in df.columns}
        if rename_map:
            df = df.rename(columns=rename_map)

        if "player_name" not in df.columns and "Player" in dataframe.columns:
            df["player_name"] = dataframe["Player"]

        if "player_name" in df.columns:
            df = df[df["player_name"].notna()].copy()
            df.loc[:, "player_name"] = df["player_name"].apply(cls._clean_player_name)
            df = df[df["player_name"].astype(str).str.strip() != ""]
            df = df[~df["player_name"].str.lower().isin(cls.INVALID_PLAYER_NAMES)]
            df = df[~df["player_name"].str.contains(r"total$", case=False, na=False)]

        if "age" in df.columns:
            df.loc[:, "age"] = df["age"].apply(cls._parse_age)

        for column in cls.INTEGER_COLUMNS:
            if column in df.columns:
                df.loc[:, column] = (
                    pd.to_numeric(df[column].astype(str).str.replace(",", ""), errors="coerce")
                    .fillna(0)
                    .astype(int)
                )

        for column in cls.FLOAT_COLUMNS:
            if column in df.columns:
                df.loc[:, column] = pd.to_numeric(
                    df[column].astype(str).str.replace(",", ""), errors="coerce"
                ).fillna(0.0)

        df = df.reset_index(drop=True)
        return df

    def get_team_squad_data(self, team_url: str) -> Optional[pd.DataFrame]:
        """
        Takım kadro verilerini çeker.

        Args:
            team_url: Takım sayfasının URL'si
            
        Returns:
            Kadro verileri içeren DataFrame
        """
        try:
            logger.info(f"Takım verileri çekiliyor: {team_url}")
            
            response = self.session.get(team_url)
            if response.status_code != 200:
                logger.error(f"Sayfa alınamadı. Status code: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, "html.parser")

            # Kadro tablosunu bul (stats_standard_* id'li tablo)
            squad_table = soup.find("table", {"id": lambda x: x and self.SQUAD_TABLE_ID_PREFIX in x})

            if not squad_table:
                logger.warning("Kadro tablosu bulunamadı")
                return None

            # Pandas ile tabloyu oku
            df = pd.read_html(str(squad_table))[0]
            df = self._normalise_squad_dataframe(df)

            team_name = ""
            season_name = None
            header = soup.find("h1")
            if header:
                header_text = header.get_text(" ", strip=True)
                season_match = re.search(r"(\d{4}-\d{4})", header_text)
                if season_match:
                    season_name = season_match.group(1)
                    header_text = header_text.replace(season_name, "").strip()
                team_name = re.sub(r"\s*Stats$", "", header_text).strip(" -")

            if not team_name:
                team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")

            if season_name:
                df.attrs["season"] = season_name
            df.attrs["team_name"] = team_name

            player_links: List[Optional[str]] = []
            table_body = squad_table.find("tbody")
            if table_body:
                for row in table_body.find_all("tr"):
                    if row.get("class") and "thead" in row.get("class"):
                        continue
                    player_cell = row.find("th", {"data-stat": "player"})
                    player_anchor = player_cell.find("a") if player_cell else None
                    if player_anchor and player_anchor.get("href"):
                        player_links.append(f"https://fbref.com{player_anchor.get('href')}")
                    else:
                        player_links.append(None)

            if player_links and len(player_links) >= len(df):
                df.loc[:, "player_url"] = player_links[: len(df)]

            logger.info(f"Kadro verileri başarıyla çekildi. {len(df)} oyuncu bulundu.")
            time.sleep(self.delay)

            return df
            
        except Exception as e:
            logger.error(f"Kadro verileri çekilirken hata: {str(e)}")
            return None
    
    def get_player_match_logs(self, player_url: str) -> Optional[pd.DataFrame]:
        """
        Oyuncu maç loglarını çeker.
        
        Args:
            player_url: Oyuncu sayfasının URL'si
            
        Returns:
            Maç logları içeren DataFrame
        """
        try:
            logger.info(f"Oyuncu maç logları çekiliyor: {player_url}")
            
            response = self.session.get(player_url)
            if response.status_code != 200:
                logger.error(f"Sayfa alınamadı. Status code: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Maç logları tablosunu bul
            match_logs_table = soup.find("table", {"id": "matchlogs_for"})
            
            if not match_logs_table:
                logger.warning("Maç logları tablosu bulunamadı")
                return None
            
            df = pd.read_html(str(match_logs_table))[0]
            
            # Çok seviyeli sütun başlıklarını düzelt
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join(col).strip() for col in df.columns.values]
            
            logger.info(f"Maç logları başarıyla çekildi. {len(df)} maç bulundu.")
            time.sleep(self.delay)
            
            return df
            
        except Exception as e:
            logger.error(f"Maç logları çekilirken hata: {str(e)}")
            return None
    
    def get_league_teams(self, league_url: str) -> List[Dict[str, str]]:
        """
        Lig sayfasından takım listesini çeker.
        
        Args:
            league_url: Lig sayfasının URL'si
            
        Returns:
            Takım bilgileri listesi
        """
        try:
            logger.info(f"Lig takımları çekiliyor: {league_url}")
            
            response = self.session.get(league_url)
            if response.status_code != 200:
                logger.error(f"Sayfa alınamadı. Status code: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Takım linklerini bul
            team_links = soup.find_all("a", href=lambda x: x and "/squads/" in x)
            
            teams = []
            for link in team_links:
                team_name = link.get_text(strip=True)
                team_url = "https://fbref.com" + link.get("href")
                
                if team_name and team_url not in [t["url"] for t in teams]:
                    teams.append({
                        "name": team_name,
                        "url": team_url
                    })
            
            logger.info(f"{len(teams)} takım bulundu.")
            time.sleep(self.delay)
            
            return teams
            
        except Exception as e:
            logger.error(f"Takım listesi çekilirken hata: {str(e)}")
            return []
    
    @staticmethod
    def _build_player_payload(row: pd.Series, team_name: str, team_url: str, season: str) -> Optional[Dict[str, Any]]:
        player_name = FBRefScraper._clean_player_name(row.get("player_name")) if "player_name" in row else FBRefScraper._clean_player_name(row.get("Player"))
        if not player_name:
            return None

        row_dict = row.where(pd.notna(row), None).to_dict()
        row_dict.setdefault("player_name", player_name)

        payload: Dict[str, Any] = {
            "team_name": team_name,
            "team_url": team_url,
            "season": season,
            "player_name": player_name,
            "player_url": row_dict.get("player_url"),
            "position": row_dict.get("position") or row_dict.get("Pos"),
            "nationality": row_dict.get("nationality") or row_dict.get("Nation"),
            "age": row_dict.get("age") or row_dict.get("Age"),
            "matches_played": row_dict.get("matches_played") or row_dict.get("MP") or 0,
            "starts": row_dict.get("starts") or row_dict.get("Starts") or 0,
            "minutes_played": row_dict.get("minutes_played") or row_dict.get("Min") or 0,
            "goals": row_dict.get("goals") or row_dict.get("Gls") or 0,
            "assists": row_dict.get("assists") or row_dict.get("Ast") or 0,
            "non_penalty_goals": row_dict.get("non_penalty_goals") or row_dict.get("G-PK") or 0,
            "goals_plus_assists": row_dict.get("goals_plus_assists") or row_dict.get("G+A") or 0,
            "non_penalty_goals_plus_assists": row_dict.get("non_penalty_goals_plus_assists") or row_dict.get("G+A-PK") or 0,
            "penalties_scored": row_dict.get("penalties_scored") or row_dict.get("PK") or 0,
            "penalties_attempted": row_dict.get("penalties_attempted") or row_dict.get("PKatt") or 0,
            "yellow_cards": row_dict.get("yellow_cards") or row_dict.get("CrdY") or 0,
            "red_cards": row_dict.get("red_cards") or row_dict.get("CrdR") or 0,
            "expected_goals": row_dict.get("expected_goals") or row_dict.get("xG") or 0.0,
            "expected_assists": row_dict.get("expected_assists") or row_dict.get("xAG") or 0.0,
            "non_penalty_expected_goals": row_dict.get("non_penalty_expected_goals") or row_dict.get("npxG") or 0.0,
            "expected_goals_plus_assists": row_dict.get("expected_goals_plus_assists") or row_dict.get("npxG+xAG") or 0.0,
            "progressive_carries": row_dict.get("progressive_carries") or row_dict.get("PrgC") or 0,
            "progressive_passes": row_dict.get("progressive_passes") or row_dict.get("PrgP") or 0,
            "progressive_passes_received": row_dict.get("progressive_passes_received") or row_dict.get("PrgR") or 0,
        }

        payload["raw_data"] = row_dict
        return payload

    def scrape_player_data(self, team_urls: List[str], seasons: List[str] = None) -> List[Dict]:
        """
        Birden fazla takımdan oyuncu verilerini çeker.
        
        Args:
            team_urls: Takım URL'leri listesi
            seasons: Sezon listesi (opsiyonel)
            
        Returns:
            Oyuncu verileri listesi
        """
        all_player_data = []
        
        for team_url in team_urls:
            try:
                # Takım kadro verilerini çek
                squad_df = self.get_team_squad_data(team_url)
                
                if squad_df is not None and not squad_df.empty:
                    team_name = squad_df.attrs.get("team_name") or team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
                    inferred_season = squad_df.attrs.get("season")
                    season_value = seasons[0] if seasons else inferred_season or "2024-2025"

                    for _, player in squad_df.iterrows():
                        player_payload = self._build_player_payload(player, team_name, team_url, season_value)
                        if player_payload:
                            all_player_data.append(player_payload)

                logger.info(f"Takım tamamlandı: {team_url}")

            except Exception as e:
                logger.error(f"Takım verisi çekilirken hata ({team_url}): {str(e)}")
                continue
        
        logger.info(f"Toplam {len(all_player_data)} oyuncu verisi çekildi.")
        return all_player_data


# Örnek kullanım fonksiyonları
def scrape_premier_league_players():
    """Premier League oyuncularını çeker."""
    scraper = FBRefScraper()
    
    # Premier League 2024-25 URL'si
    premier_league_url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    
    # Takımları çek
    teams = scraper.get_league_teams(premier_league_url)
    team_urls = [team["url"] for team in teams[:5]]  # İlk 5 takım için test
    
    # Oyuncu verilerini çek
    player_data = scraper.scrape_player_data(team_urls, ["2024-2025"])
    
    return player_data


if __name__ == "__main__":
    # Test için örnek kullanım
    player_data = scrape_premier_league_players()
    print(f"Çekilen oyuncu sayısı: {len(player_data)}")
    
    if player_data:
        print("İlk oyuncu verisi:")
        print(player_data[0])