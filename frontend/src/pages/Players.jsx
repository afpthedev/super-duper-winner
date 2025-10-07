import { useEffect, useMemo, useState } from 'react';
import { Card, Input, Select, Space, Table, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';
import { fetchPlayers, fetchTeams } from '../utils/api.js';

const { Title } = Typography;

const PAGE_SIZE = 20;

function PlayersPage() {
  const navigate = useNavigate();
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [teamOptions, setTeamOptions] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState();
  const [selectedPosition, setSelectedPosition] = useState();
  const [page, setPage] = useState(1);

  useEffect(() => {
    const loadTeams = async () => {
      try {
        const data = await fetchTeams();
        setTeamOptions(
          data.teams.map((team) => ({
            label: `${team.name}${team.league ? ` (${team.league})` : ''}`,
            value: team.id,
          })),
        );
      } catch (error) {
        console.error('Takımlar yüklenemedi', error);
      }
    };

    loadTeams();
  }, []);

  useEffect(() => {
    const loadPlayers = async () => {
      try {
        setLoading(true);
        const params = {
          limit: PAGE_SIZE,
          offset: (page - 1) * PAGE_SIZE,
        };

        if (search) {
          params.search = search;
        }
        if (selectedTeam) {
          params.team_id = selectedTeam;
        }
        if (selectedPosition) {
          params.position = selectedPosition;
        }

        const data = await fetchPlayers(params);
        setPlayers(data.players);
        setTotal(data.total);
      } catch (error) {
        console.error('Oyuncu listesi yüklenemedi', error);
      } finally {
        setLoading(false);
      }
    };

    loadPlayers();
  }, [page, search, selectedTeam, selectedPosition]);

  const positionOptions = useMemo(() => {
    const positions = new Set(players.map((player) => player.position).filter(Boolean));
    return Array.from(positions).map((position) => ({ label: position, value: position }));
  }, [players]);

  const columns = [
    {
      title: 'Oyuncu',
      dataIndex: 'name',
      key: 'name',
      render: (value) => <strong>{value}</strong>,
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
      render: (value) => (value ? <Tag color="blue">{value}</Tag> : '-'),
    },
    {
      title: 'Yaş',
      dataIndex: 'age',
      key: 'age',
      width: 80,
    },
    {
      title: 'Uyruk',
      dataIndex: 'nationality',
      key: 'nationality',
      responsive: ['lg'],
    },
  ];

  return (
    <div>
      <Title level={3} className="page-header">
        Oyuncu Analizi
      </Title>
      <Card>
        <Space className="table-actions" wrap>
          <Input.Search
            placeholder="Oyuncu ara"
            allowClear
            onSearch={(value) => {
              setPage(1);
              setSearch(value);
            }}
            style={{ minWidth: 200 }}
          />
          <Select
            allowClear
            placeholder="Takım filtresi"
            options={teamOptions}
            value={selectedTeam}
            onChange={(value) => {
              setSelectedTeam(value);
              setPage(1);
            }}
            style={{ minWidth: 200 }}
          />
          <Select
            allowClear
            placeholder="Pozisyon filtresi"
            options={positionOptions}
            value={selectedPosition}
            onChange={(value) => {
              setSelectedPosition(value);
              setPage(1);
            }}
            style={{ minWidth: 200 }}
          />
        </Space>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={players}
          columns={columns}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            onChange: (nextPage) => setPage(nextPage),
            showSizeChanger: false,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/players/${record.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </div>
  );
}

export default PlayersPage;
