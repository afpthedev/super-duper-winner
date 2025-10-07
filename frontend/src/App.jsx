import { useState } from 'react';
import { Layout, Menu, Button, Typography, message } from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  UserOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import DashboardPage from './pages/Dashboard.jsx';
import PlayersPage from './pages/Players.jsx';
import TeamsPage from './pages/Teams.jsx';
import PlayerDetailPage from './pages/PlayerDetail.jsx';
import TeamDetailPage from './pages/TeamDetail.jsx';
import { triggerScrape } from './utils/api.js';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: <Link to="/">Dashboard</Link>,
  },
  {
    key: '/players',
    icon: <UserOutlined />,
    label: <Link to="/players">Oyuncular</Link>,
  },
  {
    key: '/teams',
    icon: <TeamOutlined />,
    label: <Link to="/teams">Takımlar</Link>,
  },
];

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [scraping, setScraping] = useState(false);

  const handleTriggerScrape = async () => {
    try {
      setScraping(true);
      const response = await triggerScrape();
      if (response.success) {
        message.success(response.message);
      } else {
        message.warning(response.message || 'Scraping isteği tamamlanamadı');
      }
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Scraping başlatılırken hata oluştu');
    } finally {
      setScraping(false);
    }
  };

  return (
    <Layout hasSider>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} breakpoint="lg">
        <div
          style={{
            height: 48,
            margin: 16,
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 600,
            letterSpacing: 1,
          }}
        >
          FBRef
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} onClick={(e) => navigate(e.key)} />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Title level={3} style={{ margin: 0 }}>
            FBRef Analitik Platformu
          </Title>
          <Button
            type="primary"
            icon={<SyncOutlined spin={scraping} />}
            loading={scraping}
            onClick={handleTriggerScrape}
          >
            Veriyi Güncelle
          </Button>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24 }}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/players" element={<PlayersPage />} />
            <Route path="/players/:playerId" element={<PlayerDetailPage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/teams/:teamId" element={<TeamDetailPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
