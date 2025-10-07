"""
Flask web application for FBRef data management.
Provides web interface for viewing and managing scraped football data.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.config.settings import settings
from src.database.connection import DatabaseManager
from src.database.repository import DataService, TeamRepository, PlayerRepository, SeasonRepository
from src.database.models import Player, Team, Season, PlayerStats, MatchLog
from main import FBRefDataPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FBRefWebApp:
    """Flask web application for FBRef data management."""
    
    def __init__(self):
        self.app = Flask(__name__, template_folder='../../templates', static_folder='../../static')
        self.app.secret_key = settings.app_secret_key or 'fbref-secret-key-change-in-production'
        
        # Enable CORS
        CORS(self.app)
        
        # Initialize database
        self.db_manager = DatabaseManager()
        self.data_service = DataService(self.db_manager)
        self.team_repo = TeamRepository(self.db_manager)
        self.player_repo = PlayerRepository(self.db_manager)
        self.season_repo = SeasonRepository(self.db_manager)
        
        # Initialize scraper pipeline
        self.pipeline = FBRefDataPipeline()
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            try:
                with self.db_manager.get_session() as session:
                    # Get summary statistics
                    total_players = session.query(Player).count()
                    total_teams = session.query(Team).count()
                    total_seasons = session.query(Season).count()
                    total_stats = session.query(PlayerStats).count()
                    
                    # Get recent players
                    recent_players = session.query(Player).order_by(Player.created_at.desc()).limit(10).all()
                    
                    # Get teams with player counts
                    teams_with_counts = session.query(
                        Team.name, 
                        Team.league,
                        session.query(Player).filter(Player.current_team_id == Team.id).count().label('player_count')
                    ).all()
                    
                    return render_template('dashboard.html',
                                         total_players=total_players,
                                         total_teams=total_teams,
                                         total_seasons=total_seasons,
                                         total_stats=total_stats,
                                         recent_players=recent_players,
                                         teams_with_counts=teams_with_counts)
            except Exception as e:
                logger.error(f"Error loading dashboard: {e}")
                flash(f"Veri yüklenirken hata oluştu: {e}", 'error')
                return render_template('dashboard.html',
                                     total_players=0, total_teams=0, 
                                     total_seasons=0, total_stats=0,
                                     recent_players=[], teams_with_counts=[])
        
        @self.app.route('/players')
        def players():
            """Players listing page."""
            try:
                page = request.args.get('page', 1, type=int)
                per_page = 20
                search = request.args.get('search', '')
                team_filter = request.args.get('team', '')
                position_filter = request.args.get('position', '')
                
                with self.db_manager.get_session() as session:
                    query = session.query(Player)
                    
                    # Apply filters
                    if search:
                        query = query.filter(
                            (Player.name.ilike(f'%{search}%')) |
                            (Player.surname.ilike(f'%{search}%'))
                        )
                    
                    if team_filter:
                        query = query.join(Team).filter(Team.name.ilike(f'%{team_filter}%'))
                    
                    if position_filter:
                        query = query.filter(Player.position.ilike(f'%{position_filter}%'))
                    
                    # Pagination
                    total = query.count()
                    players_list = query.offset((page - 1) * per_page).limit(per_page).all()
                    
                    # Get all teams for filter dropdown
                    teams = session.query(Team).order_by(Team.name).all()
                    
                    # Get unique positions
                    positions = session.query(Player.position).distinct().filter(Player.position.isnot(None)).all()
                    positions = [p[0] for p in positions if p[0]]
                    
                    has_next = total > page * per_page
                    has_prev = page > 1
                    
                    return render_template('players.html',
                                         players=players_list,
                                         teams=teams,
                                         positions=positions,
                                         page=page,
                                         has_next=has_next,
                                         has_prev=has_prev,
                                         search=search,
                                         team_filter=team_filter,
                                         position_filter=position_filter,
                                         total=total)
            except Exception as e:
                logger.error(f"Error loading players: {e}")
                flash(f"Oyuncular yüklenirken hata oluştu: {e}", 'error')
                return render_template('players.html', players=[], teams=[], positions=[])
        
        @self.app.route('/player/<int:player_id>')
        def player_detail(player_id):
            """Player detail page."""
            try:
                with self.db_manager.get_session() as session:
                    player = session.query(Player).filter(Player.id == player_id).first()
                    if not player:
                        flash('Oyuncu bulunamadı', 'error')
                        return redirect(url_for('players'))
                    
                    # Get player statistics
                    stats = session.query(PlayerStats).filter(PlayerStats.player_id == player_id).all()
                    
                    # Get match logs
                    match_logs = session.query(MatchLog).filter(MatchLog.player_id == player_id).order_by(MatchLog.date.desc()).limit(20).all()
                    
                    return render_template('player_detail.html',
                                         player=player,
                                         stats=stats,
                                         match_logs=match_logs)
            except Exception as e:
                logger.error(f"Error loading player detail: {e}")
                flash(f"Oyuncu detayları yüklenirken hata oluştu: {e}", 'error')
                return redirect(url_for('players'))
        
        @self.app.route('/teams')
        def teams():
            """Teams listing page."""
            try:
                with self.db_manager.get_session() as session:
                    teams_list = session.query(Team).order_by(Team.name).all()
                    
                    # Add player counts to teams
                    teams_with_data = []
                    for team in teams_list:
                        player_count = session.query(Player).filter(Player.current_team_id == team.id).count()
                        teams_with_data.append({
                            'team': team,
                            'player_count': player_count
                        })
                    
                    return render_template('teams.html', teams_with_data=teams_with_data)
            except Exception as e:
                logger.error(f"Error loading teams: {e}")
                flash(f"Takımlar yüklenirken hata oluştu: {e}", 'error')
                return render_template('teams.html', teams_with_data=[])
        
        @self.app.route('/team/<int:team_id>')
        def team_detail(team_id):
            """Team detail page."""
            try:
                with self.db_manager.get_session() as session:
                    team = session.query(Team).filter(Team.id == team_id).first()
                    if not team:
                        flash('Takım bulunamadı', 'error')
                        return redirect(url_for('teams'))
                    
                    # Get team players
                    players_list = session.query(Player).filter(Player.current_team_id == team_id).all()
                    
                    return render_template('team_detail.html',
                                         team=team,
                                         players=players_list)
            except Exception as e:
                logger.error(f"Error loading team detail: {e}")
                flash(f"Takım detayları yüklenirken hata oluştu: {e}", 'error')
                return redirect(url_for('teams'))
        
        @self.app.route('/scraping')
        def scraping():
            """Scraping management page."""
            return render_template('scraping.html')
        
        @self.app.route('/api/scrape', methods=['POST'])
        def api_scrape():
            """API endpoint to start scraping."""
            try:
                data = request.get_json()
                mode = data.get('mode', 'test')
                team_url = data.get('team_url', '')
                season = data.get('season', '2024-2025')
                
                if mode == 'team' and not team_url:
                    return jsonify({'error': 'Takım URL\'si gerekli'}), 400
                
                # Start scraping in background (simplified for demo)
                if mode == 'test':
                    result = self.pipeline.run_test()
                elif mode == 'team':
                    result = self.pipeline.scrape_team(team_url, season)
                elif mode == 'full':
                    result = self.pipeline.run_full_pipeline(season)
                else:
                    return jsonify({'error': 'Geçersiz mod'}), 400
                
                return jsonify({
                    'success': True,
                    'message': f'Scraping başlatıldı: {mode} modu',
                    'result': str(result)
                })
                
            except Exception as e:
                logger.error(f"Scraping error: {e}")
                return jsonify({'error': f'Scraping hatası: {e}'}), 500
        
        @self.app.route('/api/stats')
        def api_stats():
            """API endpoint for dashboard statistics."""
            try:
                with self.db_manager.get_session() as session:
                    stats = {
                        'total_players': session.query(Player).count(),
                        'total_teams': session.query(Team).count(),
                        'total_seasons': session.query(Season).count(),
                        'total_stats': session.query(PlayerStats).count(),
                        'total_match_logs': session.query(MatchLog).count()
                    }
                    return jsonify(stats)
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/players')
        def api_players():
            """API endpoint for players data."""
            try:
                limit = request.args.get('limit', 100, type=int)
                offset = request.args.get('offset', 0, type=int)
                
                with self.db_manager.get_session() as session:
                    players_query = session.query(Player).offset(offset).limit(limit)
                    players_list = players_query.all()
                    
                    players_data = []
                    for player in players_list:
                        players_data.append({
                            'id': player.id,
                            'name': player.name,
                            'surname': player.surname,
                            'position': player.position,
                            'age': player.age,
                            'nationality': player.nationality,
                            'team': player.current_team.name if player.current_team else None
                        })
                    
                    return jsonify({
                        'players': players_data,
                        'total': session.query(Player).count()
                    })
            except Exception as e:
                logger.error(f"Error getting players: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.errorhandler(404)
        def not_found(error):
            return render_template('404.html'), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return render_template('500.html'), 500
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask application."""
        logger.info(f"Starting FBRef Web App on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_app():
    """Factory function to create Flask app."""
    web_app = FBRefWebApp()
    return web_app.app

if __name__ == '__main__':
    app = FBRefWebApp()
    app.run(debug=True)