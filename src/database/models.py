from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Team(Base):
    """Takım modeli"""
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    fbref_url = Column(String(500), nullable=True)
    league = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    players = relationship("Player", back_populates="team")
    
    def __repr__(self):
        return f"<Team(name='{self.name}', league='{self.league}')>"


class Season(Base):
    """Sezon modeli"""
    __tablename__ = 'seasons'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False, unique=True)  # örn: "2024-2025"
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    player_stats = relationship("PlayerStats", back_populates="season")
    
    def __repr__(self):
        return f"<Season(name='{self.name}')>"


class Player(Base):
    """Oyuncu modeli"""
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    full_name = Column(String(150), nullable=True)
    position = Column(String(20), nullable=True)
    nationality = Column(String(50), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)  # cm cinsinden
    weight = Column(Float, nullable=True)  # kg cinsinden
    fbref_url = Column(String(500), nullable=True)
    
    # Takım bilgisi
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStats", back_populates="player")
    
    def __repr__(self):
        return f"<Player(name='{self.name}', position='{self.position}')>"


class PlayerStats(Base):
    """Oyuncu istatistikleri modeli"""
    __tablename__ = 'player_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # İlişki anahtarları
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True)
    
    # Temel istatistikler
    matches_played = Column(Integer, default=0)
    starts = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    
    # Gol ve asist istatistikleri
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    penalties_scored = Column(Integer, default=0)
    penalties_attempted = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    
    # Gelişmiş istatistikler
    expected_goals = Column(Float, default=0.0)  # xG
    expected_assists = Column(Float, default=0.0)  # xA
    progressive_carries = Column(Integer, default=0)
    progressive_passes = Column(Integer, default=0)
    
    # Pas istatistikleri
    passes_completed = Column(Integer, default=0)
    passes_attempted = Column(Integer, default=0)
    pass_completion_rate = Column(Float, default=0.0)
    
    # Savunma istatistikleri
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    blocks = Column(Integer, default=0)
    clearances = Column(Integer, default=0)
    
    # Şut istatistikleri
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    shot_accuracy = Column(Float, default=0.0)
    
    # Diğer istatistikler
    touches = Column(Integer, default=0)
    dribbles_completed = Column(Integer, default=0)
    dribbles_attempted = Column(Integer, default=0)
    fouls_committed = Column(Integer, default=0)
    fouls_drawn = Column(Integer, default=0)
    
    # Meta veriler
    data_source = Column(String(50), default='fbref')
    raw_data = Column(Text, nullable=True)  # JSON formatında ham veri
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    player = relationship("Player", back_populates="stats")
    season = relationship("Season", back_populates="player_stats")
    team = relationship("Team")
    
    def __repr__(self):
        return f"<PlayerStats(player_id={self.player_id}, season_id={self.season_id}, goals={self.goals})>"


class MatchLog(Base):
    """Maç bazlı oyuncu performans verileri"""
    __tablename__ = 'match_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # İlişki anahtarları
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    
    # Maç bilgileri
    match_date = Column(DateTime, nullable=True)
    competition = Column(String(100), nullable=True)
    round_info = Column(String(50), nullable=True)
    venue = Column(String(10), nullable=True)  # Home/Away
    opponent = Column(String(100), nullable=True)
    result = Column(String(10), nullable=True)  # W/D/L
    
    # Performans verileri
    minutes_played = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    expected_goals = Column(Float, default=0.0)
    expected_assists = Column(Float, default=0.0)
    
    # Pas verileri
    passes_completed = Column(Integer, default=0)
    passes_attempted = Column(Integer, default=0)
    
    # Savunma verileri
    tackles = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    
    # Diğer veriler
    touches = Column(Integer, default=0)
    dribbles_completed = Column(Integer, default=0)
    fouls_committed = Column(Integer, default=0)
    fouls_drawn = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    
    # Meta veriler
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    player = relationship("Player")
    season = relationship("Season")
    
    def __repr__(self):
        return f"<MatchLog(player_id={self.player_id}, date={self.match_date}, opponent='{self.opponent}')>"


class ScrapingLog(Base):
    """Veri çekme işlemlerinin logları"""
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(500), nullable=False)
    scraping_type = Column(String(50), nullable=False)  # team, player, match_logs
    status = Column(String(20), nullable=False)  # success, failed, partial
    records_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True)  # saniye cinsinden
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ScrapingLog(url='{self.source_url}', status='{self.status}')>"