import { useEffect, useState } from 'react';
import { Card, Col, Input, Row, Statistic, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { fetchTeams } from '../utils/api.js';

const { Title } = Typography;

function TeamsPage() {
  const navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [filteredTeams, setFilteredTeams] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadTeams = async () => {
      try {
        setLoading(true);
        const data = await fetchTeams();
        setTeams(data.teams);
        setFilteredTeams(data.teams);
      } catch (error) {
        console.error('Takımlar yüklenemedi', error);
      } finally {
        setLoading(false);
      }
    };

    loadTeams();
  }, []);

  const handleSearch = (value) => {
    if (!value) {
      setFilteredTeams(teams);
      return;
    }

    const term = value.toLowerCase();
    setFilteredTeams(
      teams.filter((team) => team.name.toLowerCase().includes(term) || (team.league || '').toLowerCase().includes(term)),
    );
  };

  return (
    <div>
      <Title level={3} className="page-header">
        Takım Analizi
      </Title>
      <Input.Search
        placeholder="Takım ara"
        allowClear
        onSearch={handleSearch}
        style={{ maxWidth: 320, marginBottom: 24 }}
        loading={loading}
      />
      <Row gutter={[16, 16]}>
        {filteredTeams.map((team) => (
          <Col key={team.id} xs={24} md={12} lg={8} xl={6}>
            <Card
              hoverable
              onClick={() => navigate(`/teams/${team.id}`)}
              style={{ borderRadius: 12 }}
              title={team.name}
            >
              <Statistic title="Lig" value={team.league || 'Bilinmiyor'} />
              <Statistic title="Ülke" value={team.country || 'Bilinmiyor'} style={{ marginTop: 12 }} />
              <Statistic title="Oyuncu Sayısı" value={team.player_count} style={{ marginTop: 12 }} />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}

export default TeamsPage;
