import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Tag,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, MinusCircleOutlined, PlusOutlined, TeamOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchTeams } from '../utils/api.js';

const { Title, Paragraph } = Typography;

const TEAM_STORAGE_KEY = 'fbref-custom-teams';

const FORMATION_OPTIONS = [
  '4-3-3',
  '4-2-3-1',
  '4-4-2',
  '3-5-2',
  '3-4-3',
  '5-3-2',
  '4-1-4-1',
  '4-3-1-2',
  '4-5-1',
].map((value) => ({ label: value, value }));

const POSITION_OPTIONS = [
  'GK',
  'RB',
  'RWB',
  'CB',
  'LB',
  'LWB',
  'DM',
  'CM',
  'AM',
  'RM',
  'LM',
  'RW',
  'LW',
  'CF',
  'ST',
].map((value) => ({ label: value, value }));

const ROLE_OPTIONS = [
  { label: 'İlk 11', value: 'starter' },
  { label: 'Yedek', value: 'bench' },
];

const safeReadLocalTeams = () => {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(TEAM_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed;
  } catch (error) {
    console.warn('Yerel takımlar okunamadı', error);
    return [];
  }
};

const persistLocalTeams = (teams) => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(TEAM_STORAGE_KEY, JSON.stringify(teams));
  } catch (error) {
    console.warn('Yerel takımlar kaydedilemedi', error);
  }
};

const filterTeams = (teams, searchValue) => {
  if (!searchValue) {
    return teams;
  }
  const term = searchValue.toLowerCase();
  return teams.filter((team) =>
    [team.name, team.league, team.country]
      .filter(Boolean)
      .some((field) => field.toLowerCase().includes(term)),
  );
};

function TeamsPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [teams, setTeams] = useState([]);
  const [localTeams, setLocalTeams] = useState([]);
  const [searchValue, setSearchValue] = useState('');
  const [filteredTeams, setFilteredTeams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setLocalTeams(safeReadLocalTeams());
  }, []);

  useEffect(() => {
    const loadTeams = async () => {
      try {
        setLoading(true);
        const data = await fetchTeams();
        const apiTeams = Array.isArray(data?.teams) ? data.teams : [];
        setTeams(apiTeams);
      } catch (error) {
        console.error('Takımlar yüklenemedi', error);
      } finally {
        setLoading(false);
      }
    };

    loadTeams();
  }, []);

  const mergedTeams = useMemo(() => {
    return [...teams, ...localTeams];
  }, [teams, localTeams]);

  useEffect(() => {
    setFilteredTeams(filterTeams(mergedTeams, searchValue));
  }, [mergedTeams, searchValue]);

  const handleSearch = (value) => {
    setSearchValue(value);
  };

  const handleAddTeam = async () => {
    try {
      setSubmitting(true);
      const values = await form.validateFields();
      const now = Date.now();
      const teamId = `local-${now}`;
      const players = (values.players || []).map((player, index) => ({
        ...player,
        id: `local-${now}-${index}`,
        is_local: true,
        is_starter: player.role !== 'bench',
        stats: {
          goals: Number(player.goals ?? 0) || 0,
          assists: Number(player.assists ?? 0) || 0,
          minutes: Number(player.minutes ?? 0) || 0,
          xg: Number(player.xg ?? 0) || 0,
          xa: Number(player.xa ?? 0) || 0,
        },
      }));

      const newTeam = {
        id: teamId,
        name: values.name,
        league: values.league,
        country: values.country,
        description: values.description,
        preferred_formation: values.formation,
        formation: values.formation,
        metrics: {
          goals: Number(values.teamGoals ?? 0) || 0,
          xg: Number(values.teamXg ?? 0) || 0,
          xa: Number(values.teamXa ?? 0) || 0,
          possession: Number(values.teamPossession ?? 0) || 0,
        },
        players,
        player_count: players.length,
        created_at: new Date().toISOString(),
        isCustom: true,
      };

      const updatedLocalTeams = [...localTeams, newTeam];
      setLocalTeams(updatedLocalTeams);
      persistLocalTeams(updatedLocalTeams);
      message.success('Takım başarıyla eklendi');
      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      console.error('Takım ekleme başarısız', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTeam = (teamId) => {
    const updatedLocalTeams = localTeams.filter((team) => team.id !== teamId);
    setLocalTeams(updatedLocalTeams);
    persistLocalTeams(updatedLocalTeams);
    message.success('Takım kaldırıldı');
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={3} className="page-header" style={{ marginBottom: 8 }}>
            Takım Analizi
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Takımları keşfedin, özel kadrolar oluşturun ve dizilişleri yeşil sahada görselleştirin.
          </Paragraph>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          Yeni Takım Ekle
        </Button>
      </div>
      <Input.Search
        placeholder="Takım ara"
        allowClear
        onSearch={handleSearch}
        onChange={(event) => handleSearch(event.target.value)}
        style={{ maxWidth: 340, marginBottom: 24 }}
        loading={loading}
        value={searchValue}
      />
      <Row gutter={[16, 16]}>
        {filteredTeams.map((team) => {
          const isCustom = String(team.id).startsWith('local-') || team.isCustom;
          const playerCount = team.player_count || team.players?.length || 0;
          return (
            <Col key={team.id} xs={24} md={12} lg={8} xl={6}>
              <Card
                hoverable
                onClick={() => navigate(`/teams/${team.id}`)}
                style={{ borderRadius: 14, height: '100%' }}
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span>{team.name}</span>
                    {isCustom && (
                      <Tag color="green" icon={<TeamOutlined />}
                        style={{ borderRadius: 12, padding: '0 8px', fontSize: 12 }}
                      >
                        Özel Kadro
                      </Tag>
                    )}
                  </div>
                }
                extra={
                  isCustom ? (
                    <Popconfirm
                      title="Bu özel takımı kaldırmak istediğinize emin misiniz?"
                      okText="Evet"
                      cancelText="Vazgeç"
                      onConfirm={() => handleDeleteTeam(team.id)}
                    >
                      <Button
                        type="text"
                        icon={<DeleteOutlined />}
                        danger
                        onClick={(event) => event.stopPropagation()}
                      />
                    </Popconfirm>
                  ) : null
                }
              >
                <Statistic title="Lig" value={team.league || 'Bilinmiyor'} />
                <Statistic title="Ülke" value={team.country || 'Bilinmiyor'} style={{ marginTop: 12 }} />
                <Statistic
                  title="Oyuncu Sayısı"
                  value={playerCount}
                  style={{ marginTop: 12 }}
                />
                <Statistic
                  title="Tercih edilen Diziliş"
                  value={team.preferred_formation || team.formation || '4-3-3'}
                  style={{ marginTop: 12 }}
                />
              </Card>
            </Col>
          );
        })}
      </Row>

      <Modal
        title="Yeni Takım Oluştur"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleAddTeam}
        okText="Takımı Kaydet"
        confirmLoading={submitting}
        width={900}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ formation: '4-3-3', players: [] }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item name="name" label="Takım Adı" rules={[{ required: true, message: 'Takım adı gerekli' }]}>
                <Input placeholder="Ör. Galaktik FC" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="league" label="Lig" rules={[{ required: true, message: 'Lig bilgisi gerekli' }]}>
                <Input placeholder="Ör. Süper Lig" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="country" label="Ülke">
                <Input placeholder="Ülke" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="formation" label="Tercih Edilen Diziliş">
                <Select options={FORMATION_OPTIONS} showSearch allowClear={false} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="Kısa Not">
            <Input.TextArea rows={2} placeholder="Takım hakkında kısa notlar" allowClear />
          </Form.Item>

          <Row gutter={16}>
            <Col xs={24} md={6}>
              <Form.Item name="teamGoals" label="Toplam Gol">
                <InputNumber min={0} precision={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="teamXg" label="Toplam xG">
                <InputNumber min={0} precision={2} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="teamXa" label="Toplam xA">
                <InputNumber min={0} precision={2} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="teamPossession" label="Toplam Topla Oynama (%)">
                <InputNumber min={0} max={100} precision={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Title level={4} style={{ marginTop: 24 }}>
            Kadro ve Oyuncu İstatistikleri
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 12 }}>
            En az 11 oyuncu ekleyerek ilk 11 dizilimini oluşturabilirsiniz. Yedek oyuncular da eklenebilir.
          </Paragraph>

          <Form.List
            name="players"
            rules={[
              {
                validator: async (_, value) => {
                  if (!value || value.length < 11) {
                    return Promise.reject(new Error('Kadronuz en az 11 oyuncudan oluşmalıdır.'));
                  }
                  return Promise.resolve();
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => (
              <>
                {fields.map((field, index) => (
                  <Space
                    key={field.key}
                    style={{ display: 'flex', marginBottom: 8 }}
                    align="baseline"
                    wrap
                  >
                    <Form.Item
                      {...field}
                      name={[field.name, 'name']}
                      fieldKey={[field.fieldKey, 'name']}
                      label={index === 0 ? 'Oyuncu Adı' : ''}
                      rules={[{ required: true, message: 'Oyuncu adı gerekli' }]}
                    >
                      <Input placeholder="Oyuncu adı" allowClear />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'position']}
                      fieldKey={[field.fieldKey, 'position']}
                      label={index === 0 ? 'Mevki' : ''}
                      rules={[{ required: true, message: 'Mevki gerekli' }]}
                    >
                      <Select
                        options={POSITION_OPTIONS}
                        placeholder="Mevki"
                        style={{ minWidth: 110 }}
                      />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'role']}
                      fieldKey={[field.fieldKey, 'role']}
                      label={index === 0 ? 'Rol' : ''}
                      initialValue="starter"
                    >
                      <Select options={ROLE_OPTIONS} style={{ minWidth: 120 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'number']}
                      fieldKey={[field.fieldKey, 'number']}
                      label={index === 0 ? 'Forma No' : ''}
                    >
                      <InputNumber min={0} max={99} style={{ width: 90 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'minutes']}
                      fieldKey={[field.fieldKey, 'minutes']}
                      label={index === 0 ? 'Dakika' : ''}
                    >
                      <InputNumber min={0} style={{ width: 110 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'goals']}
                      fieldKey={[field.fieldKey, 'goals']}
                      label={index === 0 ? 'Gol' : ''}
                    >
                      <InputNumber min={0} style={{ width: 90 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'assists']}
                      fieldKey={[field.fieldKey, 'assists']}
                      label={index === 0 ? 'Asist' : ''}
                    >
                      <InputNumber min={0} style={{ width: 90 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'xg']}
                      fieldKey={[field.fieldKey, 'xg']}
                      label={index === 0 ? 'xG' : ''}
                    >
                      <InputNumber min={0} step={0.1} style={{ width: 90 }} />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'xa']}
                      fieldKey={[field.fieldKey, 'xa']}
                      label={index === 0 ? 'xA' : ''}
                    >
                      <InputNumber min={0} step={0.1} style={{ width: 90 }} />
                    </Form.Item>
                    {fields.length > 1 ? (
                      <MinusCircleOutlined onClick={() => remove(field.name)} />
                    ) : null}
                  </Space>
                ))}
                <Form.Item>
                  <Button
                    type="dashed"
                    onClick={() => add({ role: 'starter' })}
                    block
                    icon={<PlusOutlined />}
                  >
                    Oyuncu Ekle
                  </Button>
                  <Form.ErrorList errors={errors} />
                </Form.Item>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}

export default TeamsPage;
