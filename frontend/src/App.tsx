import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import GeneratePage from "./pages/GeneratePage";
import AnalysisPage from "./pages/AnalysisPage";
import HowItWorksPage from "./pages/HowItWorksPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
