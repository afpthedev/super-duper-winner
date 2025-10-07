import { useEffect, useState } from 'react';
import { Card, Descriptions, Empty, List, Skeleton, Statistic, Tag, Typography } from 'antd';
import { useParams } from 'react-router-dom';
import { fetchPlayer } from '../utils/api.js';

const { Title } = Typography;

function PlayerDetailPage() {
  const { playerId } = useParams();
  const [player, setPlayer] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadPlayer = async () => {
      try {
        setLoading(true);
        const data = await fetchPlayer(playerId);
        setPlayer(data);
      } catch (error) {
        console.error('Oyuncu bilgisi alınamadı', error);
      } finally {
        setLoading(false);
      }
    };

    loadPlayer();
  }, [playerId]);

  if (loading) {
    return <Skeleton active paragraph={{ rows: 6 }} />;
  }

  if (!player) {
    return <Empty description="Oyuncu bulunamadı" />;
  }

  return (
    <div>
      <Title level={3} className="page-header">
        {player.name}
      </Title>
      <Card style={{ marginBottom: 24 }}>
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label="Takım">{player.team || 'Bilinmiyor'}</Descriptions.Item>
          <Descriptions.Item label="Pozisyon">
            {player.position ? <Tag color="blue">{player.position}</Tag> : 'Bilinmiyor'}
          </Descriptions.Item>
          <Descriptions.Item label="Yaş">{player.age || 'Bilinmiyor'}</Descriptions.Item>
          <Descriptions.Item label="Uyruk">{player.nationality || 'Bilinmiyor'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Sezon Bazlı Performans">
        {player.stats.length ? (
          <List
            itemLayout="horizontal"
            dataSource={player.stats}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={item.season}
                  description={
                    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                      <Statistic title="Maç" value={item.matches_played} />
                      <Statistic title="Dakika" value={item.minutes_played} />
                      <Statistic title="Gol" value={item.goals} />
                      <Statistic title="Asist" value={item.assists} />
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <Empty description="İstatistik bulunamadı" />
        )}
      </Card>
    </div>
  );
}

export default PlayerDetailPage;
