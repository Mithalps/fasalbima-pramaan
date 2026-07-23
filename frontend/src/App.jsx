import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LanguageProvider } from "./context/LanguageContext";
import LandingPage from "./pages/LandingPage";
import NewClaimPage from "./pages/NewClaimPage";
import SuccessPage from "./pages/SuccessPage";
import ViewClaimPage from "./pages/ViewClaimPage";

function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/claims/new" element={<NewClaimPage />} />
          <Route path="/claims/:claimId/success" element={<SuccessPage />} />
          <Route path="/claims/:claimId" element={<ViewClaimPage />} />
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  );
}

export default App;
