from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.database.connection import (
    get_db_session_dependency,
    get_db_manager,
    init_database,
)
from src.database.models import MatchLog, Player, PlayerStats, Season, Team
from main import FBRefDataPipeline

from .schemas import (
    OperationResult,
    PlayerDetail,
    PlayerListItem,
    PlayerListResponse,
    PlayerStatsSchema,
    ScrapeRequest,
    ScrapeResponse,
    SummaryStats,
    TeamCreateRequest,
    TeamDetail,
    TeamListItem,
    TeamListResponse,
    TeamUpdateRequest,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="FBRef Football Data API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    """Ensure database tables are created on startup."""
    logger.info("Initialising database during startup")
    init_database()


@app.get("/health", response_model=dict)
def healthcheck() -> dict:
    """Simple healthcheck endpoint."""
    manager = get_db_manager()
    return {"status": "ok", "database": manager.test_connection()}


@app.get("/api/summary", response_model=SummaryStats)
def get_summary(session: Session = Depends(get_db_session_dependency)) -> SummaryStats:
    """Return summary statistics for dashboard view."""
    total_players = session.query(Player).count()
    total_teams = session.query(Team).count()
    total_seasons = session.query(Season).count()
    total_stats = session.query(PlayerStats).count()
    total_match_logs = session.query(MatchLog).count()

    return SummaryStats(
        total_players=total_players,
        total_teams=total_teams,
        total_seasons=total_seasons,
        total_stats=total_stats,
        total_match_logs=total_match_logs,
    )


@app.get("/api/players", response_model=PlayerListResponse)
def list_players(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(default=None, description="Oyuncu adına göre arama"),
    team_id: Optional[int] = Query(default=None, description="Takıma göre filtre"),
    position: Optional[str] = Query(default=None, description="Pozisyona göre filtre"),
    session: Session = Depends(get_db_session_dependency),
) -> PlayerListResponse:
    """List players with optional filters and pagination."""
    query = session.query(Player)

    if search:
        pattern = f"%{search}%"
        query = query.filter(Player.name.ilike(pattern))

    if team_id:
        query = query.filter(Player.team_id == team_id)

    if position:
        query = query.filter(Player.position.ilike(f"%{position}%"))

    total = query.count()
    players = query.order_by(Player.name).offset(offset).limit(limit).all()

    player_items = [
        PlayerListItem(
            id=player.id,
            name=player.name,
            position=player.position,
            age=player.age,
            team=player.team.name if player.team else None,
            nationality=player.nationality,
        )
        for player in players
    ]

    return PlayerListResponse(players=player_items, total=total, limit=limit, offset=offset)


@app.get("/api/players/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, session: Session = Depends(get_db_session_dependency)) -> PlayerDetail:
    """Retrieve a single player with aggregated season statistics."""
    player = session.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Oyuncu bulunamadı")

    stats_records = (
        session.query(PlayerStats)
        .filter(PlayerStats.player_id == player_id)
        .order_by(PlayerStats.season_id.desc())
        .all()
    )

    stats_payload: List[PlayerStatsSchema] = []
    for record in stats_records:
        season_name = record.season.name if record.season else "Bilinmiyor"
        stats_payload.append(
            PlayerStatsSchema(
                season=season_name,
                matches_played=record.matches_played,
                minutes_played=record.minutes_played,
                goals=record.goals,
                assists=record.assists,
            )
        )

    return PlayerDetail(
        id=player.id,
        name=player.name,
        position=player.position,
        age=player.age,
        team=player.team.name if player.team else None,
        nationality=player.nationality,
        stats=stats_payload,
    )


@app.get("/api/teams", response_model=TeamListResponse)
def list_teams(
    search: Optional[str] = Query(default=None, description="Takım adına göre arama"),
    session: Session = Depends(get_db_session_dependency),
) -> TeamListResponse:
    """List teams including player counts."""
    query = session.query(Team)

    if search:
        query = query.filter(Team.name.ilike(f"%{search}%"))

    teams = query.order_by(Team.name).all()

    team_items = []
    for team in teams:
        player_count = session.query(Player).filter(Player.team_id == team.id).count()
        team_items.append(
            TeamListItem(
                id=team.id,
                name=team.name,
                league=team.league,
                country=team.country,
                player_count=player_count,
            )
        )

    return TeamListResponse(teams=team_items, total=len(team_items))


@app.get("/api/teams/{team_id}", response_model=TeamDetail)
def get_team(team_id: int, session: Session = Depends(get_db_session_dependency)) -> TeamDetail:
    """Retrieve team information alongside players."""
    team = session.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Takım bulunamadı")

    players = session.query(Player).filter(Player.team_id == team_id).order_by(Player.name).all()

    player_items = [
        PlayerListItem(
            id=player.id,
            name=player.name,
            position=player.position,
            age=player.age,
            team=team.name,
            nationality=player.nationality,
        )
        for player in players
    ]

    return TeamDetail(
        id=team.id,
        name=team.name,
        league=team.league,
        country=team.country,
        fbref_url=team.fbref_url,
        players=player_items,
    )


@app.post("/api/teams", response_model=TeamDetail, status_code=201)
def create_team(
    request: TeamCreateRequest,
    session: Session = Depends(get_db_session_dependency),
) -> TeamDetail:
    """Create a new team record."""
    existing = session.query(Team).filter(Team.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu isimde bir takım zaten mevcut")

    team = Team(
        name=request.name,
        league=request.league,
        country=request.country,
        fbref_url=request.fbref_url,
    )
    session.add(team)
    session.commit()
    session.refresh(team)

    return TeamDetail(
        id=team.id,
        name=team.name,
        league=team.league,
        country=team.country,
        fbref_url=team.fbref_url,
        players=[],
    )


@app.put("/api/teams/{team_id}", response_model=TeamDetail)
def update_team(
    team_id: int,
    request: TeamUpdateRequest,
    session: Session = Depends(get_db_session_dependency),
) -> TeamDetail:
    """Update an existing team."""
    team = session.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Takım bulunamadı")

    if request.name and request.name != team.name:
        existing = session.query(Team).filter(Team.name == request.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Bu isimde bir takım zaten mevcut")

    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(team, field, value)

    session.commit()
    session.refresh(team)

    players = (
        session.query(Player)
        .filter(Player.team_id == team.id)
        .order_by(Player.name)
        .all()
    )
    player_items = [
        PlayerListItem(
            id=player.id,
            name=player.name,
            position=player.position,
            age=player.age,
            team=team.name,
            nationality=player.nationality,
        )
        for player in players
    ]

    return TeamDetail(
        id=team.id,
        name=team.name,
        league=team.league,
        country=team.country,
        fbref_url=team.fbref_url,
        players=player_items,
    )


@app.delete("/api/teams/{team_id}", response_model=OperationResult)
def delete_team(
    team_id: int,
    session: Session = Depends(get_db_session_dependency),
) -> OperationResult:
    """Delete a team and detach its players."""
    team = session.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Takım bulunamadı")

    players = session.query(Player).filter(Player.team_id == team_id).all()
    for player in players:
        player.team_id = None

    session.delete(team)
    session.commit()

    return OperationResult(success=True, message="Takım başarıyla silindi")


def _run_scrape_job(request: ScrapeRequest) -> str:
    """Worker function that runs scraping pipeline."""
    pipeline = FBRefDataPipeline()
    if request.mode == "full":
        league_urls = request.leagues
        result = pipeline.run_full_pipeline(league_urls, [request.season] if request.season else None)
        return "Tam lig veri çekme tamamlandı" if result else "Lig veri çekme başarısız"

    if request.mode == "team":
        if not request.team_url:
            raise ValueError("Takım modu için takım URL'si gerekli")
        result = pipeline.run_single_team(request.team_url, request.season)
        return "Takım verisi çekildi" if result else "Takım verisi çekilemedi"

    result = pipeline.run_single_team(
        team_url="https://fbref.com/en/squads/18bb7c10/Arsenal-Stats",
        season=request.season,
    )
    return "Test modu tamamlandı" if result else "Test modu başarısız"


@app.post("/api/scrape", response_model=ScrapeResponse)
def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
) -> ScrapeResponse:
    """Trigger scraping pipeline in the background."""
    try:
        background_tasks.add_task(_run_scrape_job, request)
        message = "Scraping görevi arka planda başlatıldı"
        return ScrapeResponse(success=True, message=message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - beklenmeyen hatalar
        logger.exception("Scraping başlatılırken hata")
        raise HTTPException(status_code=500, detail="Scraping başlatılamadı") from exc


__all__ = ["app"]
