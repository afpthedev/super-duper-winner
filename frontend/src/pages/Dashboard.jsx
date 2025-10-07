import { useEffect, useState } from 'react';
import { Card, Col, Empty, Row, Skeleton, Statistic, Table, Typography } from 'antd';
import { fetchPlayers, fetchSummary } from '../utils/api.js';

const { Title, Paragraph } = Typography;

const playerColumns = [
  {
    title: 'Oyuncu',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: 'Takım',
    dataIndex: 'team',
    key: 'team',
  },
  {
    title: 'Pozisyon',
    dataIndex: 'position',
    key: 'position',
    responsive: ['md'],
  },
  {
    title: 'Yaş',
    dataIndex: 'age',
    key: 'age',
    width: 80,
  },
];

function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [topPlayers, setTopPlayers] = useState([]);
  const [loadingPlayers, setLoadingPlayers] = useState(false);

  useEffect(() => {
    const loadSummary = async () => {
      try {
        setLoadingSummary(true);
        const data = await fetchSummary();
        setSummary(data);
      } catch (error) {
        console.error('Summary yüklenemedi', error);
      } finally {
        setLoadingSummary(false);
      }
    };

    const loadPlayers = async () => {
      try {
        setLoadingPlayers(true);
        const data = await fetchPlayers({ limit: 10 });
        setTopPlayers(data.players);
      } catch (error) {
        console.error('Oyuncular yüklenemedi', error);
      } finally {
        setLoadingPlayers(false);
      }
    };

    loadSummary();
    loadPlayers();
  }, []);

  return (
    <div>
      <Title level={3} className="page-header">
        Genel Bakış
      </Title>
      <Paragraph>
        FBRef platformundan çekilen verilerin hızlı bir özetini görüntüleyin. Scraper modülünü kullanarak oyuncu ve takım istatistiklerini
        güncel tutabilirsiniz.
      </Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} lg={6}>
          <Card bordered className="chart-card">
            {loadingSummary ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic title="Oyuncu Sayısı" value={summary?.total_players ?? 0} />
            )}
          </Card>
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Card bordered className="chart-card">
            {loadingSummary ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic title="Takım Sayısı" value={summary?.total_teams ?? 0} />
            )}
          </Card>
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Card bordered className="chart-card">
            {loadingSummary ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic title="Sezon Sayısı" value={summary?.total_seasons ?? 0} />
            )}
          </Card>
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Card bordered className="chart-card">
            {loadingSummary ? (
              <Skeleton active paragraph={false} />
            ) : (
              <Statistic title="İstatistik Kaydı" value={summary?.total_stats ?? 0} />
            )}
          </Card>
        </Col>
      </Row>

      <Card title="Son Eklenen Oyuncular" style={{ marginTop: 24 }}>
        {loadingPlayers ? (
          <Skeleton active />
        ) : topPlayers.length ? (
          <Table
            rowKey="id"
            dataSource={topPlayers}
            columns={playerColumns}
            pagination={false}
            locale={{ emptyText: 'Oyuncu verisi bulunamadı' }}
          />
        ) : (
          <Empty description="Oyuncu verisi bulunamadı" />
        )}
      </Card>
    </div>
  );
}

export default DashboardPage;
