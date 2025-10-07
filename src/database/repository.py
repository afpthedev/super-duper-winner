import json
import math
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
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

    @staticmethod
    def _normalise_string(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _coerce_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if math.isnan(value):
                return default
            return int(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if not cleaned:
                return default
            try:
                numeric_value = float(cleaned)
            except ValueError:
                return default
            if math.isnan(numeric_value):
                return default
            return int(numeric_value)
        return default

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                return default
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if not cleaned:
                return default
            try:
                numeric_value = float(cleaned)
            except ValueError:
                return default
            if math.isnan(numeric_value):
                return default
            return numeric_value
        return default

    @staticmethod
    def _replace_nan(value: Any) -> Any:
        if isinstance(value, float) and math.isnan(value):
            return None
        if isinstance(value, dict):
            return {key: DataService._replace_nan(val) for key, val in value.items()}
        if isinstance(value, list):
            return [DataService._replace_nan(item) for item in value]
        return value

    @staticmethod
    def _parse_season_bounds(season_name: str) -> Tuple[int, int]:
        cleaned = DataService._normalise_string(season_name)
        match = re.search(r"(\d{4})\s*[-–]\s*(\d{4})", cleaned)
        if match:
            return int(match.group(1)), int(match.group(2))
        single_match = re.search(r"(\d{4})", cleaned)
        if single_match:
            start_year = int(single_match.group(1))
            return start_year, start_year + 1
        current_year = datetime.utcnow().year
        return current_year, current_year + 1

    def save_player_data(self, player_data_list: List[Dict]) -> Dict[str, int]:
        """Oyuncu verilerini toplu olarak kaydeder."""
        stats = {"teams": 0, "players": 0, "stats": 0, "errors": 0}
        processed_team_ids: Set[int] = set()
        processed_player_ids: Set[int] = set()

        with get_db_session_context() as session:
            for player_data in player_data_list:
                try:
                    team_name = self._normalise_string(player_data.get("team_name"))
                    if not team_name:
                        logger.warning("Takım adı bulunamadı, kayıt atlandı")
                        stats["errors"] += 1
                        continue

                    team = self.team_repo.get_or_create(
                        session,
                        name=team_name,
                        fbref_url=self._normalise_string(player_data.get("team_url")) or None
                    )
                    if team.id not in processed_team_ids:
                        processed_team_ids.add(team.id)
                        stats["teams"] += 1

                    season_name = self._normalise_string(player_data.get("season")) or "2024-2025"
                    start_year, end_year = self._parse_season_bounds(season_name)
                    season = self.season_repo.get_or_create(
                        session, season_name, start_year, end_year
                    )

                    player_name = self._normalise_string(player_data.get("player_name"))
                    if not player_name:
                        logger.warning("Oyuncu adı bulunamadı, kayıt atlandı (takım: %s)", team_name)
                        stats["errors"] += 1
                        continue

                    player_position = self._normalise_string(player_data.get("position")) or None
                    player_nationality = self._normalise_string(player_data.get("nationality")) or None
                    player_fbref_url = self._normalise_string(player_data.get("player_url")) or None
                    player_age = self._coerce_int(player_data.get("age"), default=None)

                    player = self.player_repo.get_or_create(
                        session,
                        name=player_name,
                        team_id=team.id,
                        position=player_position,
                        age=player_age,
                        nationality=player_nationality,
                        fbref_url=player_fbref_url
                    )
                    if player.id not in processed_player_ids:
                        processed_player_ids.add(player.id)
                        stats["players"] += 1

                    player_updates: Dict[str, Any] = {}
                    if player_position and player.position != player_position:
                        player_updates["position"] = player_position
                    if player_nationality and player.nationality != player_nationality:
                        player_updates["nationality"] = player_nationality
                    if player_age is not None and player.age != player_age:
                        player_updates["age"] = player_age
                    if player_fbref_url and player.fbref_url != player_fbref_url:
                        player_updates["fbref_url"] = player_fbref_url

                    if player_updates:
                        self.player_repo.update(session, player.id, **player_updates)

                    matches_played = self._coerce_int(player_data.get("matches_played"), default=0) or 0
                    starts = self._coerce_int(player_data.get("starts"), default=0) or 0
                    minutes_source = player_data.get("minutes_played", player_data.get("minutes"))
                    minutes_played = self._coerce_int(minutes_source, default=0) or 0
                    goals = self._coerce_int(player_data.get("goals"), default=0) or 0
                    assists = self._coerce_int(player_data.get("assists"), default=0) or 0
                    penalties_scored = self._coerce_int(player_data.get("penalties_scored"), default=0) or 0
                    penalties_attempted = self._coerce_int(player_data.get("penalties_attempted"), default=0) or 0
                    yellow_cards = self._coerce_int(player_data.get("yellow_cards"), default=0) or 0
                    red_cards = self._coerce_int(player_data.get("red_cards"), default=0) or 0
                    expected_goals = self._coerce_float(player_data.get("expected_goals"), default=0.0)
                    expected_assists = self._coerce_float(player_data.get("expected_assists"), default=0.0)
                    progressive_carries = self._coerce_int(player_data.get("progressive_carries"), default=0) or 0
                    progressive_passes = self._coerce_int(player_data.get("progressive_passes"), default=0) or 0

                    raw_payload = player_data.get("raw_data") or player_data
                    raw_payload = self._replace_nan(raw_payload)
                    raw_data_json = json.dumps(raw_payload, ensure_ascii=False)

                    existing_stats = self.stats_repo.get_by_player_and_season(session, player.id, season.id)
                    stats_values = {
                        "team_id": team.id,
                        "matches_played": matches_played,
                        "starts": starts,
                        "minutes_played": minutes_played,
                        "goals": goals,
                        "assists": assists,
                        "penalties_scored": penalties_scored,
                        "penalties_attempted": penalties_attempted,
                        "yellow_cards": yellow_cards,
                        "red_cards": red_cards,
                        "expected_goals": expected_goals,
                        "expected_assists": expected_assists,
                        "progressive_carries": progressive_carries,
                        "progressive_passes": progressive_passes,
                        "raw_data": raw_data_json,
                    }

                    if existing_stats:
                        for key, value in stats_values.items():
                            setattr(existing_stats, key, value)
                        existing_stats.updated_at = datetime.utcnow()
                    else:
                        self.stats_repo.create(
                            session,
                            player_id=player.id,
                            season_id=season.id,
                            **stats_values
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