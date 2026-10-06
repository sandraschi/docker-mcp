import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { Chat } from "@/pages/chat";
import { Compose } from "@/pages/compose";
import { ContainerDetail } from "@/pages/container-detail";
import { Containers } from "@/pages/containers";
import { Dashboard } from "@/pages/dashboard";
import { Examples } from "@/pages/examples";
import { Help } from "@/pages/help";
import { ImageDetail } from "@/pages/image-detail";
import { Images } from "@/pages/images";
import { LogsPage } from "@/pages/logs";
import { NetworkDetail } from "@/pages/network-detail";
import { Networks } from "@/pages/networks";
import { Reports } from "@/pages/reports";
import { Settings } from "@/pages/settings";
import { ToolRunner } from "@/pages/tool-runner";
import { Tools } from "@/pages/tools";
import { VolumeDetail } from "@/pages/volume-detail";
import { Volumes } from "@/pages/volumes";

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/containers/:id" element={<ContainerDetail />} />
          <Route path="/containers" element={<Containers />} />
          <Route path="/images/:id" element={<ImageDetail />} />
          <Route path="/images" element={<Images />} />
          <Route path="/volumes/:id" element={<VolumeDetail />} />
          <Route path="/volumes" element={<Volumes />} />
          <Route path="/networks/:id" element={<NetworkDetail />} />
          <Route path="/networks" element={<Networks />} />
          <Route path="/compose" element={<Compose />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/tools/:name" element={<ToolRunner />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/examples" element={<Examples />} />
          <Route path="/help" element={<Help />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/compose" element={<Compose />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}

export default App;
