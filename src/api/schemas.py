from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SummaryStats(BaseModel):
    total_players: int = Field(..., description="Toplam oyuncu sayısı")
    total_teams: int = Field(..., description="Toplam takım sayısı")
    total_seasons: int = Field(..., description="Toplam sezon sayısı")
    total_stats: int = Field(..., description="Toplam istatistik kaydı")
    total_match_logs: int = Field(..., description="Toplam maç logu")


class PlayerStatsSchema(BaseModel):
    season: str
    matches_played: Optional[int] = 0
    minutes_played: Optional[int] = 0
    goals: Optional[int] = 0
    assists: Optional[int] = 0


class PlayerListItem(BaseModel):
    id: int
    name: str
    position: Optional[str]
    age: Optional[int]
    team: Optional[str]
    nationality: Optional[str]


class PlayerListResponse(BaseModel):
    players: List[PlayerListItem]
    total: int
    limit: int
    offset: int


class PlayerDetail(BaseModel):
    id: int
    name: str
    position: Optional[str]
    age: Optional[int]
    team: Optional[str]
    nationality: Optional[str]
    stats: List[PlayerStatsSchema]


class TeamListItem(BaseModel):
    id: int
    name: str
    league: Optional[str]
    country: Optional[str]
    player_count: int


class TeamListResponse(BaseModel):
    teams: List[TeamListItem]
    total: int


class TeamDetail(BaseModel):
    id: int
    name: str
    league: Optional[str]
    country: Optional[str]
    fbref_url: Optional[str]
    players: List[PlayerListItem]


class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    league: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=50)
    fbref_url: Optional[str] = Field(default=None, max_length=500)


class TeamUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    league: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=50)
    fbref_url: Optional[str] = Field(default=None, max_length=500)


class OperationResult(BaseModel):
    success: bool
    message: str


class ScrapeRequest(BaseModel):
    mode: str = Field(default="test", description="Çalışma modu: test, team veya full")
    team_url: Optional[str] = None
    season: Optional[str] = None
    leagues: Optional[List[str]] = None


class ScrapeResponse(BaseModel):
    success: bool
    message: str
    details: Optional[str] = None
