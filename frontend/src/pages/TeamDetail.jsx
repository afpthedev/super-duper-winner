import { useEffect, useState } from 'react';
import { Card, Empty, List, Skeleton, Statistic, Tag, Typography } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchTeam } from '../utils/api.js';

const { Title } = Typography;

function TeamDetailPage() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadTeam = async () => {
      try {
        setLoading(true);
        const data = await fetchTeam(teamId);
        setTeam(data);
      } catch (error) {
        console.error('Takım bilgisi alınamadı', error);
      } finally {
        setLoading(false);
      }
    };

    loadTeam();
  }, [teamId]);

  if (loading) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  if (!team) {
    return <Empty description="Takım bulunamadı" />;
  }

  return (
    <div>
      <Title level={3} className="page-header">
        {team.name}
      </Title>
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          <Statistic title="Lig" value={team.league || 'Bilinmiyor'} />
          <Statistic title="Ülke" value={team.country || 'Bilinmiyor'} />
          <Statistic title="Oyuncu Sayısı" value={team.players.length} />
        </div>
      </Card>

      <Card title="Kadrodaki Oyuncular">
        {team.players.length ? (
          <List
            itemLayout="horizontal"
            dataSource={team.players}
            renderItem={(player) => (
              <List.Item onClick={() => navigate(`/players/${player.id}`)} style={{ cursor: 'pointer' }}>
                <List.Item.Meta
                  title={player.name}
                  description={
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      {player.position && <Tag color="geekblue">{player.position}</Tag>}
                      <span>Yaş: {player.age || '-'}</span>
                      {player.nationality && <span>Ülke: {player.nationality}</span>}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <Empty description="Oyuncu bulunamadı" />
        )}
      </Card>
    </div>
  );
}

export default TeamDetailPage;
