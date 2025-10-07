#!/usr/bin/env python3
"""
FBRef Futbolcu Veri Çekme Uygulaması
Ana uygulama dosyası - scraping ve veritabanı işlemlerini koordine eder
"""

import logging
import time
import sys
import os
from typing import List, Dict

# Proje kök dizinini Python path'ine ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.scraper.fbref_scraper import FBRefScraper
from src.database.connection import init_database, get_db_manager
from src.database.repository import data_service
from src.config.settings import get_settings

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class FBRefDataPipeline:
    """FBRef veri çekme ve işleme pipeline'ı"""
    
    def __init__(self):
        self.settings = get_settings()
        self.scraper = FBRefScraper(
            headless=self.settings.scraping.headless_browser,
            delay=self.settings.scraping.delay_between_requests
        )
        
    def initialize_database(self):
        """Veritabanını başlatır"""
        try:
            logger.info("Veritabanı başlatılıyor...")
            init_database()
            logger.info("Veritabanı başarıyla başlatıldı")
            return True
        except Exception as e:
            logger.error(f"Veritabanı başlatılamadı: {str(e)}")
            return False
    
    def scrape_league_data(self, league_urls: List[str], seasons: List[str] = None) -> List[Dict]:
        """Lig verilerini çeker"""
        all_player_data = []
        
        if seasons is None:
            seasons = [self.settings.scraping.default_season]
        
        logger.info(f"Veri çekme başlıyor. {len(league_urls)} lig, {len(seasons)} sezon")
        
        for league_url in league_urls:
            try:
                logger.info(f"Lig işleniyor: {league_url}")
                
                # Lig takımlarını çek
                teams = self.scraper.get_league_teams(league_url)
                logger.info(f"{len(teams)} takım bulundu")
                
                if not teams:
                    logger.warning(f"Takım bulunamadı: {league_url}")
                    continue
                
                # Takım URL'lerini hazırla
                team_urls = [team["url"] for team in teams]
                
                # Oyuncu verilerini çek
                player_data = self.scraper.scrape_player_data(team_urls, seasons)
                all_player_data.extend(player_data)
                
                logger.info(f"Lig tamamlandı: {league_url}, {len(player_data)} oyuncu")
                
            except Exception as e:
                logger.error(f"Lig verisi çekilemedi ({league_url}): {str(e)}")
                continue
        
        logger.info(f"Toplam {len(all_player_data)} oyuncu verisi çekildi")
        return all_player_data
    
    def save_data_to_database(self, player_data: List[Dict]) -> Dict[str, int]:
        """Verileri veritabanına kaydeder"""
        try:
            logger.info(f"{len(player_data)} oyuncu verisi kaydediliyor...")
            stats = data_service.save_player_data(player_data)
            logger.info(f"Veri kaydetme tamamlandı: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Veri kaydedilemedi: {str(e)}")
            return {"error": str(e)}
    
    def run_full_pipeline(self, league_urls: List[str] = None, seasons: List[str] = None):
        """Tam pipeline'ı çalıştırır"""
        start_time = time.time()
        
        try:
            # Veritabanını başlat
            if not self.initialize_database():
                return False
            
            # Varsayılan lig URL'leri
            if league_urls is None:
                league_urls = [
                    "https://fbref.com/en/comps/9/Premier-League-Stats",  # Premier League
                    "https://fbref.com/en/comps/12/La-Liga-Stats",       # La Liga
                    "https://fbref.com/en/comps/20/Bundesliga-Stats",    # Bundesliga
                ]
            
            # Verileri çek
            player_data = self.scrape_league_data(league_urls, seasons)
            
            if not player_data:
                logger.warning("Çekilecek veri bulunamadı")
                return False
            
            # Veritabanına kaydet
            save_stats = self.save_data_to_database(player_data)
            
            # Özet bilgi
            execution_time = time.time() - start_time
            logger.info(f"Pipeline tamamlandı. Süre: {execution_time:.2f} saniye")
            logger.info(f"Sonuçlar: {save_stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline hatası: {str(e)}")
            return False
        
        finally:
            # Kaynakları temizle
            self.scraper.close_driver()
    
    def run_single_team(self, team_url: str, season: str = None):
        """Tek takım için veri çeker"""
        try:
            if season is None:
                season = self.settings.scraping.default_season
            
            logger.info(f"Tek takım verisi çekiliyor: {team_url}")
            
            # Veritabanını başlat
            if not self.initialize_database():
                return False
            
            # Takım verilerini çek
            player_data = self.scraper.scrape_player_data([team_url], [season])
            
            if player_data:
                # Veritabanına kaydet
                save_stats = self.save_data_to_database(player_data)
                logger.info(f"Takım verisi kaydedildi: {save_stats}")
                return True
            else:
                logger.warning("Takım verisi çekilemedi")
                return False
                
        except Exception as e:
            logger.error(f"Tek takım işlemi hatası: {str(e)}")
            return False
        
        finally:
            self.scraper.close_driver()


def main():
    """Ana fonksiyon"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FBRef Futbolcu Veri Çekme Uygulaması')
    parser.add_argument('--mode', choices=['full', 'team', 'test'], default='test',
                       help='Çalışma modu (full: tüm ligler, team: tek takım, test: test modu)')
    parser.add_argument('--team-url', type=str,
                       help='Tek takım modu için takım URL\'si')
    parser.add_argument('--season', type=str, default='2024-2025',
                       help='Sezon (örn: 2024-2025)')
    parser.add_argument('--leagues', nargs='+',
                       help='İşlenecek lig URL\'leri')
    
    args = parser.parse_args()
    
    # Logs dizinini oluştur
    os.makedirs('logs', exist_ok=True)
    
    pipeline = FBRefDataPipeline()
    
    if args.mode == 'full':
        # Tüm ligler için çalıştır
        league_urls = args.leagues or [
            "https://fbref.com/en/comps/9/Premier-League-Stats",
            "https://fbref.com/en/comps/12/La-Liga-Stats",
        ]
        success = pipeline.run_full_pipeline(league_urls, [args.season])
        
    elif args.mode == 'team':
        # Tek takım için çalıştır
        if not args.team_url:
            logger.error("Tek takım modu için --team-url parametresi gerekli")
            return False
        success = pipeline.run_single_team(args.team_url, args.season)
        
    elif args.mode == 'test':
        # Test modu - sadece bir takım
        test_team_url = "https://fbref.com/en/squads/18bb7c10/Arsenal-Stats"
        success = pipeline.run_single_team(test_team_url, args.season)
    
    if success:
        logger.info("Uygulama başarıyla tamamlandı")
        return 0
    else:
        logger.error("Uygulama hata ile sonlandı")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)