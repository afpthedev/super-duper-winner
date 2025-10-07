import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  List,
  Row,
  Select,
  Skeleton,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { ArrowLeftOutlined, LineChartOutlined, TeamOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchTeam } from '../utils/api.js';

const { Title, Paragraph } = Typography;

const TEAM_STORAGE_KEY = 'fbref-custom-teams';

const formationOptions = ['4-3-3', '4-2-3-1', '4-4-2', '3-5-2', '3-4-3', '5-3-2', '4-1-4-1'];

const STARTER_KEYS = ['is_starter', 'isStarter', 'is_starting', 'starting', 'starter', 'start', 'in_starting_xi'];

const STAT_PATHS = {
  minutes: [
    ['minutes'],
    ['stats', 'minutes'],
    ['statistics', 'minutes'],
    ['summary', 'minutes'],
    ['minutes_played'],
    ['games', 'minutes'],
    ['details', 'minutes_played'],
  ],
  goals: [['goals'], ['stats', 'goals'], ['statistics', 'goals'], ['summary', 'goals'], ['details', 'goals']],
  assists: [['assists'], ['stats', 'assists'], ['statistics', 'assists'], ['summary', 'assists'], ['details', 'assists']],
  xg: [
    ['xg'],
    ['stats', 'xg'],
    ['advanced', 'xg'],
    ['expected_goals'],
    ['metrics', 'xg'],
    ['details', 'xg'],
  ],
  xa: [
    ['xa'],
    ['stats', 'xa'],
    ['advanced', 'xa'],
    ['expected_assists'],
    ['metrics', 'xa'],
    ['details', 'xa'],
  ],
  matches: [
    ['matches'],
    ['stats', 'matches'],
    ['statistics', 'matches'],
    ['summary', 'matches'],
    ['appearances'],
    ['games', 'appearances'],
  ],
  shots: [
    ['shots'],
    ['stats', 'shots'],
    ['statistics', 'shots'],
    ['summary', 'shots'],
    ['details', 'shots'],
  ],
};

const readLocalTeams = () => {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(TEAM_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Yerel takım verisi okunamadı', error);
    return [];
  }
};

const getNestedValue = (obj, path) => {
  return path.reduce((acc, key) => {
    if (acc !== null && acc !== undefined && Object.prototype.hasOwnProperty.call(acc, key)) {
      return acc[key];
    }
    return undefined;
  }, obj);
};

const pickValue = (obj, paths) => {
  for (const path of paths) {
    const value = getNestedValue(obj, path);
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }
  return undefined;
};

const toNumber = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
};

const formatNumber = (value, digits = 1) => {
  if (value === null || value === undefined) {
    return '-';
  }
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return '-';
  }
  return num.toFixed(digits);
};

const parseFormation = (formation) => {
  if (!formation) {
    return [4, 3, 3];
  }
  const tokens = String(formation)
    .split(/[^0-9]/)
    .map((part) => Number(part))
    .filter((part) => Number.isFinite(part) && part > 0);
  return tokens.length ? tokens : [4, 3, 3];
};

const parseNumericLike = (value) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const normalized = value.replace(',', '.');
    const asNumber = Number(normalized);
    if (Number.isFinite(asNumber)) {
      return asNumber;
    }
    const asFloat = parseFloat(normalized);
    if (Number.isFinite(asFloat)) {
      return asFloat;
    }
  }
  return null;
};

const getPlayerIdentifier = (player) => {
  return (
    player?.id ??
    player?.player_id ??
    player?.slug ??
    player?.uuid ??
    (player?.name ? `${player.name}-${player.position || ''}` : undefined)
  );
};

const isStarter = (player) => {
  if (!player) {
    return false;
  }
  if (player.role && player.role !== 'bench') {
    return true;
  }
  if (player.is_local && player.is_starter) {
    return true;
  }
  return STARTER_KEYS.some((key) => {
    const value = player[key];
    if (typeof value === 'boolean') {
      return value;
    }
    if (typeof value === 'string') {
      const normalized = value.toLowerCase();
      return ['true', 'starter', 'starting', 'yes', 'xi'].includes(normalized);
    }
    return false;
  });
};

const computeFirstEleven = (players = []) => {
  if (!players.length) {
    return [];
  }
  const starters = players.filter(isStarter);
  const seen = new Set();
  const firstEleven = [];
  const minutesSorted = [...players].sort((a, b) => {
    const minutesB = toNumber(pickValue(b, STAT_PATHS.minutes));
    const minutesA = toNumber(pickValue(a, STAT_PATHS.minutes));
    return minutesB - minutesA;
  });

  const pushPlayer = (player) => {
    const identifier = getPlayerIdentifier(player);
    if (!identifier || seen.has(identifier)) {
      return;
    }
    seen.add(identifier);
    firstEleven.push(player);
  };

  starters.forEach(pushPlayer);
  minutesSorted.forEach((player) => {
    if (firstEleven.length < 11) {
      pushPlayer(player);
    }
  });
  players.forEach((player) => {
    if (firstEleven.length < 11) {
      pushPlayer(player);
    }
  });

  return firstEleven.slice(0, 11);
};

const buildPitchLayout = (players = [], formation) => {
  if (!players.length) {
    return [];
  }
  const formationNumbers = parseFormation(formation);

  const goalkeeper = players.find((player) => {
    const position = String(player?.position || '').toUpperCase();
    return position.includes('GK') || position.includes('KAL');
  }) || players[0];

  const goalkeeperId = getPlayerIdentifier(goalkeeper);
  const outfieldPlayers = players.filter((player) => getPlayerIdentifier(player) !== goalkeeperId);

  const lines = [];
  let cursor = 0;
  formationNumbers.forEach((count) => {
    const slice = outfieldPlayers.slice(cursor, cursor + count);
    lines.push(slice);
    cursor += count;
  });
  if (cursor < outfieldPlayers.length && lines.length) {
    lines[lines.length - 1] = [...lines[lines.length - 1], ...outfieldPlayers.slice(cursor)];
  }

  const reversed = [...lines].reverse();
  const verticalStart = 12;
  const verticalEnd = 72;
  const verticalStep = reversed.length > 1 ? (verticalEnd - verticalStart) / (reversed.length - 1) : 0;

  const layout = [];
  reversed.forEach((linePlayers, rowIndex) => {
    if (!linePlayers.length) {
      return;
    }
    const top = verticalStart + rowIndex * verticalStep;
    const gap = 100 / (linePlayers.length + 1);
    linePlayers.forEach((player, index) => {
      layout.push({
        player,
        style: {
          top: `${top}%`,
          left: `${gap * (index + 1)}%`,
        },
      });
    });
  });

  layout.push({
    player: goalkeeper,
    style: {
      top: '84%',
      left: '50%',
    },
  });

  return layout;
};

const inferFormationFromPlayers = (players = []) => {
  if (!players.length) {
    return '4-3-3';
  }
  const firstEleven = computeFirstEleven(players);
  const defence = ['CB', 'LB', 'RB', 'LCB', 'RCB', 'DEF', 'LWB', 'RWB'];
  const midfield = ['DM', 'CDM', 'CM', 'LCM', 'RCM', 'AM', 'CAM', 'LM', 'RM', 'MID'];
  let defenders = 0;
  let midfielders = 0;
  let forwards = 0;

  firstEleven.forEach((player) => {
    const position = String(player?.position || '').toUpperCase();
    if (position.includes('GK')) {
      return;
    }
    if (defence.some((tag) => position.includes(tag))) {
      defenders += 1;
    } else if (midfield.some((tag) => position.includes(tag))) {
      midfielders += 1;
    } else {
      forwards += 1;
    }
  });

  const totalOutfield = defenders + midfielders + forwards;
  if (totalOutfield < 10) {
    const missing = 10 - totalOutfield;
    forwards += missing;
  }

  return `${Math.max(defenders, 3)}-${Math.max(midfielders, 2)}-${Math.max(forwards, 1)}`;
};

function TeamDetailPage() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedFormation, setSelectedFormation] = useState('4-3-3');
  const [error, setError] = useState(null);

  useEffect(() => {
    let ignore = false;
    const isLocalTeam = String(teamId).startsWith('local-');

    const loadTeam = async () => {
      try {
        setLoading(true);
        setError(null);
        if (isLocalTeam) {
          const localTeam = readLocalTeams().find((item) => String(item.id) === String(teamId));
          setTeam(localTeam || null);
          if (!localTeam) {
            setError('Takım bilgisi bulunamadı');
          }
        } else {
          const data = await fetchTeam(teamId);
          if (!ignore) {
            setTeam(data);
          }
        }
      } catch (err) {
        console.error('Takım bilgisi alınamadı', err);
        const localTeam = readLocalTeams().find((item) => String(item.id) === String(teamId));
        if (localTeam) {
          setTeam(localTeam);
        } else {
          setError('Takım verisi yüklenemedi');
          setTeam(null);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    loadTeam();

    return () => {
      ignore = true;
    };
  }, [teamId]);

  useEffect(() => {
    if (!team) {
      return;
    }
    const derivedFormation =
      team.preferred_formation || team.formation || inferFormationFromPlayers(team.players);
    setSelectedFormation(derivedFormation);
  }, [team?.id]);

  const players = team?.players || [];
  const firstEleven = useMemo(() => computeFirstEleven(players), [players]);

  const benchPlayers = useMemo(() => {
    const firstElevenIds = new Set(firstEleven.map((player) => getPlayerIdentifier(player)));
    return players.filter((player) => !firstElevenIds.has(getPlayerIdentifier(player)));
  }, [players, firstEleven]);

  const pitchLayout = useMemo(
    () => buildPitchLayout(firstEleven, selectedFormation),
    [firstEleven, selectedFormation],
  );

  const metrics = team?.metrics || {};
  const metricsPossessionNumber = parseNumericLike(metrics.possession);
  const metricsPossessionValue =
    metricsPossessionNumber !== null ? Number(metricsPossessionNumber.toFixed(1)) : metrics.possession;

  const aggregatedStats = useMemo(() => {
    if (!players.length) {
      return { goals: 0, assists: 0, xg: 0, xa: 0, minutes: 0, matches: 0, avgAge: null };
    }
    const totals = players.reduce(
      (acc, player) => {
        acc.goals += toNumber(pickValue(player, STAT_PATHS.goals));
        acc.assists += toNumber(pickValue(player, STAT_PATHS.assists));
        acc.xg += toNumber(pickValue(player, STAT_PATHS.xg));
        acc.xa += toNumber(pickValue(player, STAT_PATHS.xa));
        acc.minutes += toNumber(pickValue(player, STAT_PATHS.minutes));
        acc.matches += toNumber(pickValue(player, STAT_PATHS.matches));
        const age = Number(player.age);
        if (Number.isFinite(age)) {
          acc.ages.push(age);
        }
        return acc;
      },
      { goals: 0, assists: 0, xg: 0, xa: 0, minutes: 0, matches: 0, ages: [] },
    );

    const avgAge = totals.ages.length
      ? (totals.ages.reduce((sum, age) => sum + age, 0) / totals.ages.length).toFixed(1)
      : null;

    const { ages, ...rest } = totals;
    return { ...rest, avgAge };
  }, [players]);

  const columns = useMemo(
    () => [
      {
        title: 'Oyuncu',
        dataIndex: 'name',
        key: 'name',
        fixed: 'left',
        render: (value, record) => (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontWeight: 600 }}>{value}</span>
            <span style={{ fontSize: 12, color: '#8c8c8c' }}>{record.position}</span>
          </div>
        ),
      },
      {
        title: 'Rol',
        dataIndex: 'role',
        key: 'role',
        render: (role) => (
          <Tag color={role === 'İlk 11' ? 'green' : 'blue'}>{role}</Tag>
        ),
      },
      {
        title: 'Forma',
        dataIndex: 'number',
        key: 'number',
        align: 'center',
      },
      {
        title: 'Maç',
        dataIndex: 'matches',
        key: 'matches',
        align: 'center',
      },
      {
        title: 'Dakika',
        dataIndex: 'minutes',
        key: 'minutes',
        align: 'center',
      },
      {
        title: 'Gol',
        dataIndex: 'goals',
        key: 'goals',
        align: 'center',
      },
      {
        title: 'Asist',
        dataIndex: 'assists',
        key: 'assists',
        align: 'center',
      },
      {
        title: 'Şut',
        dataIndex: 'shots',
        key: 'shots',
        align: 'center',
      },
      {
        title: 'xG',
        dataIndex: 'xg',
        key: 'xg',
        align: 'center',
      },
      {
        title: 'xA',
        dataIndex: 'xa',
        key: 'xa',
        align: 'center',
      },
    ],
    [],
  );

  const playerRows = useMemo(() => {
    const firstElevenIds = new Set(firstEleven.map((player) => getPlayerIdentifier(player)));
    return players.map((player) => {
      const identifier = getPlayerIdentifier(player) || player.name;
      const role = firstElevenIds.has(identifier) ? 'İlk 11' : 'Yedek';
      const minutes = pickValue(player, STAT_PATHS.minutes);
      const matches = pickValue(player, STAT_PATHS.matches);
      const goals = pickValue(player, STAT_PATHS.goals);
      const assists = pickValue(player, STAT_PATHS.assists);
      const xg = pickValue(player, STAT_PATHS.xg);
      const xa = pickValue(player, STAT_PATHS.xa);
      const shots = pickValue(player, STAT_PATHS.shots);

      return {
        key: identifier,
        name: player.name,
        position: player.position || '-',
        role,
        number: player.number ?? player.shirtNumber ?? '-',
        matches: matches ?? '-',
        minutes: minutes ?? '-',
        goals: goals ?? '-',
        assists: assists ?? '-',
        xg: typeof xg === 'number' ? xg.toFixed(2) : xg ?? '-',
        xa: typeof xa === 'number' ? xa.toFixed(2) : xa ?? '-',
        shots: shots ?? '-',
      };
    });
  }, [players, firstEleven]);

  if (loading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  if (!team) {
    return <Empty description={error || 'Takım bulunamadı'} />;
  }

  return (
    <div className="team-detail-page">
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        Geri Dön
      </Button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <Title level={3} style={{ margin: 0 }}>
          {team.name}
        </Title>
        <Tag color="blue">{team.league || 'Lig Bilgisi Yok'}</Tag>
        {team.country && <Tag color="geekblue">{team.country}</Tag>}
        {String(team.id).startsWith('local-') && (
          <Tag color="green" icon={<TeamOutlined />}>Özel Kadro</Tag>
        )}
      </div>
      {team.description && (
        <Paragraph type="secondary" style={{ marginTop: 8, maxWidth: 680 }}>
          {team.description}
        </Paragraph>
      )}
      {error && (
        <Alert style={{ marginTop: 16 }} message={error} type="warning" showIcon />
      )}

      <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
        <Col xs={24} xl={16}>
          <Card
            title="Diziliş ve İlk 11"
            extra={
              <Select
                value={selectedFormation}
                onChange={setSelectedFormation}
                options={[...new Set([selectedFormation, team.preferred_formation, team.formation, ...formationOptions])]
                  .filter(Boolean)
                  .map((value) => ({ label: value, value }))}
                style={{ minWidth: 140 }}
              />
            }
          >
            {pitchLayout.length ? (
              <div className="team-pitch-wrapper">
                <div className="team-pitch">
                  <div className="pitch-half pitch-half--top" />
                  <div className="pitch-half pitch-half--bottom" />
                  <div className="pitch-center-circle" />
                  <div className="pitch-center-line" />
                  <div className="pitch-penalty pitch-penalty--top" />
                  <div className="pitch-penalty pitch-penalty--bottom" />
                  {pitchLayout.map(({ player, style }) => {
                    const identifier = getPlayerIdentifier(player) || player.name;
                    const goals = pickValue(player, STAT_PATHS.goals);
                    const xg = pickValue(player, STAT_PATHS.xg);
                    const assists = pickValue(player, STAT_PATHS.assists);
                    return (
                      <div key={identifier} className="pitch-player" style={style}>
                        <div className="pitch-player__number">{player.number ?? player.shirtNumber ?? '-'}</div>
                        <div className="pitch-player__name">{player.name}</div>
                        <div className="pitch-player__meta">
                          <span>{player.position || ''}</span>
                          {goals !== undefined && goals !== null && goals !== '' && (
                            <span>G:{goals}</span>
                          )}
                          {xg !== undefined && xg !== null && xg !== '' && (
                            <span>xG:{formatNumber(xg, 2)}</span>
                          )}
                          {assists !== undefined && assists !== null && assists !== '' && (
                            <span>A:{assists}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="pitch-legend">
                  <Tag icon={<LineChartOutlined />} color="processing">
                    Oyuncu kartlarında gol, asist ve xG değerleri görüntülenir
                  </Tag>
                </div>
              </div>
            ) : (
              <Empty description="İlk 11 bilgisi bulunamadı" />
            )}
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Takım Özeti">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic title="Toplam Gol" value={aggregatedStats.goals || 0} />
              </Col>
              <Col span={12}>
                <Statistic title="Toplam Asist" value={aggregatedStats.assists || 0} />
              </Col>
              <Col span={12}>
                <Statistic title="Toplam xG" value={formatNumber(aggregatedStats.xg, 2)} />
              </Col>
              <Col span={12}>
                <Statistic title="Toplam xA" value={formatNumber(aggregatedStats.xa, 2)} />
              </Col>
              <Col span={12}>
                <Statistic title="Toplam Dakika" value={aggregatedStats.minutes || 0} />
              </Col>
              <Col span={12}>
                <Statistic title="Maç" value={aggregatedStats.matches || players.length || 0} />
              </Col>
            </Row>
            {aggregatedStats.avgAge && (
              <div style={{ marginTop: 16 }}>
                <Statistic title="Ortalama Yaş" value={aggregatedStats.avgAge} />
              </div>
            )}
            {team.metrics && (
              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                {team.metrics.goals !== undefined && team.metrics.goals !== null && (
                  <Col span={12}>
                    <Statistic title="Sezon Golleri" value={team.metrics.goals} />
                  </Col>
                )}
                {team.metrics.xg !== undefined && team.metrics.xg !== null && (
                  <Col span={12}>
                    <Statistic title="Sezon xG" value={formatNumber(team.metrics.xg, 2)} />
                  </Col>
                )}
                {team.metrics.xa !== undefined && team.metrics.xa !== null && (
                  <Col span={12}>
                    <Statistic title="Sezon xA" value={formatNumber(team.metrics.xa, 2)} />
                  </Col>
                )}
                {team.metrics.possession !== undefined && team.metrics.possession !== null && (
                  <Col span={12}>
                    <Statistic
                      title="Topla Oynama"
                      value={
                        metricsPossessionNumber !== null ? metricsPossessionValue : team.metrics.possession
                      }
                      suffix={metricsPossessionNumber !== null ? '%' : undefined}
                    />
                  </Col>
                )}
              </Row>
            )}
          </Card>

          {benchPlayers.length > 0 && (
            <Card title="Yedek Kulübesi" style={{ marginTop: 24 }}>
              <List
                dataSource={benchPlayers}
                renderItem={(player) => {
                  const xg = pickValue(player, STAT_PATHS.xg);
                  const assists = pickValue(player, STAT_PATHS.assists);
                  return (
                    <List.Item>
                      <List.Item.Meta
                        title={player.name}
                        description={
                          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12 }}>
                            <span>Mevki: {player.position || '-'}</span>
                            {player.number && <span>Forma: {player.number}</span>}
                            {xg !== undefined && xg !== null && xg !== '' && (
                              <span>xG: {formatNumber(xg, 2)}</span>
                            )}
                            {assists !== undefined && assists !== null && assists !== '' && (
                              <span>Asist: {assists}</span>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  );
                }}
              />
            </Card>
          )}
        </Col>
      </Row>

      <Card title="Oyuncu İstatistikleri" style={{ marginTop: 24 }}>
        <Table
          columns={columns}
          dataSource={playerRows}
          pagination={{ pageSize: 15, showSizeChanger: false }}
          scroll={{ x: true }}
        />
      </Card>
    </div>
  );
}

export default TeamDetailPage;
