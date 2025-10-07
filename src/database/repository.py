import json
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, desc

from .models import Team, Player, PlayerStats, Season, MatchLog, ScrapingLog
from .connection import get_db_session_context

logger = logging.getLogger(__name__)


class BaseRepository:
    """Temel repository sınıfı"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def create(self, session: Session, **kwargs) -> Any:
        """Yeni kayıt oluşturur."""
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.flush()
            return instance
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Kayıt oluşturulamadı: {str(e)}")
            raise
    
    def get_by_id(self, session: Session, id: int) -> Optional[Any]:
        """ID ile kayıt getirir."""
        return session.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self, session: Session, limit: int = None) -> List[Any]:
        """Tüm kayıtları getirir."""
        query = session.query(self.model_class)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def update(self, session: Session, id: int, **kwargs) -> Optional[Any]:
        """Kayıt günceller."""
        instance = self.get_by_id(session, id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            instance.updated_at = datetime.utcnow()
            session.flush()
        return instance
    
    def delete(self, session: Session, id: int) -> bool:
        """Kayıt siler."""
        instance = self.get_by_id(session, id)
        if instance:
            session.delete(instance)
            session.flush()
            return True
        return False


class TeamRepository(BaseRepository):
    """Takım repository sınıfı"""
    
    def __init__(self):
        super().__init__(Team)
    
    def get_by_name(self, session: Session, name: str) -> Optional[Team]:
        """İsim ile takım getirir."""
        return session.query(Team).filter(Team.name == name).first()
    
    def get_or_create(self, session: Session, name: str, **kwargs) -> Team:
        """Takımı getirir, yoksa oluşturur."""
        team = self.get_by_name(session, name)
        if not team:
            team = self.create(session, name=name, **kwargs)
        return team
    
    def get_by_league(self, session: Session, league: str) -> List[Team]:
        """Lige göre takımları getirir."""
        return session.query(Team).filter(Team.league == league).all()


class PlayerRepository(BaseRepository):
    """Oyuncu repository sınıfı"""
    
    def __init__(self):
        super().__init__(Player)
    
    def get_by_name_and_team(self, session: Session, name: str, team_id: int) -> Optional[Player]:
        """İsim ve takım ile oyuncu getirir."""
        return session.query(Player).filter(
            and_(Player.name == name, Player.team_id == team_id)
        ).first()
    
    def get_or_create(self, session: Session, name: str, team_id: int, **kwargs) -> Player:
        """Oyuncuyu getirir, yoksa oluşturur."""
        player = self.get_by_name_and_team(session, name, team_id)
        if not player:
            player = self.create(session, name=name, team_id=team_id, **kwargs)
        return player
    
    def get_by_team(self, session: Session, team_id: int) -> List[Player]:
        """Takıma göre oyuncuları getirir."""
        return session.query(Player).filter(Player.team_id == team_id).all()
    
    def get_by_position(self, session: Session, position: str) -> List[Player]:
        """Pozisyona göre oyuncuları getirir."""
        return session.query(Player).filter(Player.position == position).all()
    
    def search_by_name(self, session: Session, name_pattern: str) -> List[Player]:
        """İsim ile oyuncu arar."""
        return session.query(Player).filter(
            Player.name.ilike(f"%{name_pattern}%")
        ).all()


class SeasonRepository(BaseRepository):
    """Sezon repository sınıfı"""
    
    def __init__(self):
        super().__init__(Season)
    
    def get_by_name(self, session: Session, name: str) -> Optional[Season]:
        """İsim ile sezon getirir."""
        return session.query(Season).filter(Season.name == name).first()
    
    def get_or_create(self, session: Session, name: str, start_year: int, end_year: int) -> Season:
        """Sezonu getirir, yoksa oluşturur."""
        season = self.get_by_name(session, name)
        if not season:
            season = self.create(
                session, 
                name=name, 
                start_year=start_year, 
                end_year=end_year
            )
        return season
    
    def get_active_seasons(self, session: Session) -> List[Season]:
        """Aktif sezonları getirir."""
        return session.query(Season).filter(Season.is_active == True).all()


class PlayerStatsRepository(BaseRepository):
    """Oyuncu istatistikleri repository sınıfı"""
    
    def __init__(self):
        super().__init__(PlayerStats)
    
    def get_by_player_and_season(self, session: Session, player_id: int, season_id: int) -> Optional[PlayerStats]:
        """Oyuncu ve sezona göre istatistik getirir."""
        return session.query(PlayerStats).filter(
            and_(PlayerStats.player_id == player_id, PlayerStats.season_id == season_id)
        ).first()
    
    def get_or_create(self, session: Session, player_id: int, season_id: int, **kwargs) -> PlayerStats:
        """İstatistiği getirir, yoksa oluşturur."""
        stats = self.get_by_player_and_season(session, player_id, season_id)
        if not stats:
            stats = self.create(session, player_id=player_id, season_id=season_id, **kwargs)
        return stats
    
    def get_by_season(self, session: Session, season_id: int, limit: int = None) -> List[PlayerStats]:
        """Sezona göre istatistikleri getirir."""
        query = session.query(PlayerStats).filter(PlayerStats.season_id == season_id)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_top_scorers(self, session: Session, season_id: int, limit: int = 10) -> List[PlayerStats]:
        """En çok gol atan oyuncuları getirir."""
        return session.query(PlayerStats).filter(
            PlayerStats.season_id == season_id
        ).order_by(desc(PlayerStats.goals)).limit(limit).all()
    
    def get_top_assisters(self, session: Session, season_id: int, limit: int = 10) -> List[PlayerStats]:
        """En çok asist yapan oyuncuları getirir."""
        return session.query(PlayerStats).filter(
            PlayerStats.season_id == season_id
        ).order_by(desc(PlayerStats.assists)).limit(limit).all()


class MatchLogRepository(BaseRepository):
    """Maç logu repository sınıfı"""
    
    def __init__(self):
        super().__init__(MatchLog)
    
    def get_by_player_and_date(self, session: Session, player_id: int, match_date: datetime) -> Optional[MatchLog]:
        """Oyuncu ve tarihe göre maç logu getirir."""
        return session.query(MatchLog).filter(
            and_(MatchLog.player_id == player_id, MatchLog.match_date == match_date)
        ).first()
    
    def get_by_player(self, session: Session, player_id: int, season_id: int = None) -> List[MatchLog]:
        """Oyuncuya göre maç loglarını getirir."""
        query = session.query(MatchLog).filter(MatchLog.player_id == player_id)
        if season_id:
            query = query.filter(MatchLog.season_id == season_id)
        return query.order_by(desc(MatchLog.match_date)).all()


class ScrapingLogRepository(BaseRepository):
    """Scraping logu repository sınıfı"""
    
    def __init__(self):
        super().__init__(ScrapingLog)
    
    def log_scraping_attempt(self, session: Session, source_url: str, scraping_type: str, 
                           status: str, records_count: int = 0, error_message: str = None,
                           execution_time: float = None) -> ScrapingLog:
        """Scraping işlemini loglar."""
        return self.create(
            session,
            source_url=source_url,
            scraping_type=scraping_type,
            status=status,
            records_count=records_count,
            error_message=error_message,
            execution_time=execution_time
        )
    
    def get_recent_logs(self, session: Session, limit: int = 50) -> List[ScrapingLog]:
        """Son scraping loglarını getirir."""
        return session.query(ScrapingLog).order_by(
            desc(ScrapingLog.created_at)
        ).limit(limit).all()


class DataService:
    """Veri işlemleri için yüksek seviye servis sınıfı"""
    
    def __init__(self):
        self.team_repo = TeamRepository()
        self.player_repo = PlayerRepository()
        self.season_repo = SeasonRepository()
        self.stats_repo = PlayerStatsRepository()
        self.match_log_repo = MatchLogRepository()
        self.scraping_log_repo = ScrapingLogRepository()
    
    def save_player_data(self, player_data_list: List[Dict]) -> Dict[str, int]:
        """Oyuncu verilerini toplu olarak kaydeder."""
        stats = {"teams": 0, "players": 0, "stats": 0, "errors": 0}
        
        with get_db_session_context() as session:
            for player_data in player_data_list:
                try:
                    # Takımı kaydet/getir
                    team = self.team_repo.get_or_create(
                        session,
                        name=player_data.get("team_name", ""),
                        fbref_url=player_data.get("team_url", "")
                    )
                    stats["teams"] += 1
                    
                    # Sezonu kaydet/getir
                    season_name = player_data.get("season", "2024-2025")
                    start_year = int(season_name.split("-")[0])
                    end_year = int(season_name.split("-")[1])
                    season = self.season_repo.get_or_create(
                        session, season_name, start_year, end_year
                    )
                    
                    # Oyuncuyu kaydet/getir
                    player = self.player_repo.get_or_create(
                        session,
                        name=player_data.get("player_name", ""),
                        team_id=team.id,
                        position=player_data.get("position", ""),
                        age=player_data.get("age")
                    )
                    stats["players"] += 1
                    
                    # İstatistikleri kaydet/güncelle
                    player_stats = self.stats_repo.get_or_create(
                        session,
                        player_id=player.id,
                        season_id=season.id,
                        team_id=team.id,
                        matches_played=player_data.get("matches_played", 0),
                        starts=player_data.get("starts", 0),
                        minutes_played=player_data.get("minutes", 0),
                        goals=player_data.get("goals", 0),
                        assists=player_data.get("assists", 0),
                        raw_data=json.dumps(player_data)
                    )
                    stats["stats"] += 1
                    
                except Exception as e:
                    logger.error(f"Oyuncu verisi kaydedilemedi: {str(e)}")
                    stats["errors"] += 1
                    continue
        
        logger.info(f"Veri kaydetme tamamlandı: {stats}")
        return stats
    
    def get_team_players_with_stats(self, team_name: str, season_name: str = None) -> List[Dict]:
        """Takım oyuncularını istatistikleriyle birlikte getirir."""
        with get_db_session_context() as session:
            team = self.team_repo.get_by_name(session, team_name)
            if not team:
                return []
            
            players = self.player_repo.get_by_team(session, team.id)
            result = []
            
            for player in players:
                player_dict = {
                    "id": player.id,
                    "name": player.name,
                    "position": player.position,
                    "age": player.age,
                    "team": team.name
                }
                
                # İstatistikleri ekle
                if season_name:
                    season = self.season_repo.get_by_name(session, season_name)
                    if season:
                        stats = self.stats_repo.get_by_player_and_season(
                            session, player.id, season.id
                        )
                        if stats:
                            player_dict.update({
                                "matches_played": stats.matches_played,
                                "goals": stats.goals,
                                "assists": stats.assists,
                                "minutes_played": stats.minutes_played
                            })
                
                result.append(player_dict)
            
            return result


# Global servis instance'ı
data_service = DataService()