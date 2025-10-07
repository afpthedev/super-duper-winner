import requests
import pandas as pd
import time
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict, Optional
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FBRefScraper:
    """
    FBRef sitesinden futbolcu verilerini çekmek için scraper sınıfı.
    Makaledeki yaklaşımı temel alarak geliştirilmiştir.
    """
    
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
            squad_table = soup.find("table", {"id": lambda x: x and "stats_standard" in x})
            
            if not squad_table:
                logger.warning("Kadro tablosu bulunamadı")
                return None
            
            # Pandas ile tabloyu oku
            df = pd.read_html(str(squad_table))[0]
            
            # Çok seviyeli sütun başlıklarını düzelt
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join(col).strip() for col in df.columns.values]
            
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
                    # Takım adını URL'den çıkar
                    team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
                    
                    # Her oyuncu için veri hazırla
                    for _, player in squad_df.iterrows():
                        player_data = {
                            "team_name": team_name,
                            "team_url": team_url,
                            "player_name": player.get("Player", ""),
                            "position": player.get("Pos", ""),
                            "age": player.get("Age", ""),
                            "matches_played": player.get("MP", 0),
                            "starts": player.get("Starts", 0),
                            "minutes": player.get("Min", 0),
                            "goals": player.get("Gls", 0),
                            "assists": player.get("Ast", 0),
                            "season": seasons[0] if seasons else "2024-2025"
                        }
                        
                        # Diğer istatistikleri de ekle
                        for col in squad_df.columns:
                            if col not in player_data:
                                player_data[col] = player.get(col, "")
                        
                        all_player_data.append(player_data)
                
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