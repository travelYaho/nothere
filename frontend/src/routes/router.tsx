import { Navigate, createBrowserRouter, useParams } from "react-router-dom"
import { MobileLayout } from "@/components/layout/MobileLayout"
import HomeGuest from "@/pages/HomeGuest"
import Login from "@/pages/Login"
import Home from "@/pages/Home"
import Bookmarks from "@/pages/Bookmarks"
import TripConditions from "@/pages/TripConditions"
import TripPlaces from "@/pages/TripPlaces"
import CustomPlace from "@/pages/CustomPlace"
import TripAnalysisLoading from "@/pages/TripAnalysisLoading"
import GuideExplore from "@/pages/GuideExplore"
import GuideLiked from "@/pages/GuideLiked"
import CompareAlternatives from "@/pages/CompareAlternatives"
import RecommendationPurpose from "@/pages/RecommendationPurpose"
import ReplacementPreviewPage from "@/pages/ReplacementPreview"
import RemainingCongested from "@/pages/RemainingCongested"
import ConfirmTrip from "@/pages/ConfirmTrip"
import SavedTrip from "@/pages/SavedTrip"
import Guidebook from "@/pages/Guidebook"
import SharedGuide from "@/pages/SharedGuide"
import MyPage from "@/pages/MyPage"

/**
 * 예전엔 STEP3 완료 후 이 경로에서 모든 장소의 방문 목적을 먼저 물어봤다(TripPurposeForm).
 * 그 화면이 모으던 데이터는 STEP4/STEP6 어디서도 읽히지 않았고, "대안 찾기"에서 그
 * 장소 하나만 물어보는 화면(RecommendationPurpose, /places/:tripPlaceId/purpose)이 이미
 * 따로 있어 중복이었다(2026-09-16, 이슈4). 화면은 제거하고 기존 라우트는 리다이렉트로
 * 유지한다 — 이 경로로 들어오는 남은 북마크·뒤로가기·직접 URL 접근이 끊어지지 않도록.
 */
function TripPurposeRedirect() {
  const { tripId } = useParams<{ tripId: string }>()
  return <Navigate to={`/trips/${tripId}/analysis`} replace />
}

export const router = createBrowserRouter([
  {
    element: <MobileLayout />,
    children: [
      { path: "/", element: <HomeGuest /> },
      { path: "/login", element: <Login /> },
      { path: "/home", element: <Home /> },
      { path: "/bookmarks", element: <Bookmarks /> },
      { path: "/trips/new", element: <TripConditions /> },
      { path: "/trips/:tripId/conditions", element: <TripConditions /> },
      { path: "/trips/:tripId/places", element: <TripPlaces /> },
      { path: "/trips/:tripId/places/custom", element: <CustomPlace /> },
      { path: "/trips/:tripId/purpose", element: <TripPurposeRedirect /> },
      { path: "/trips/:tripId/analysis", element: <TripAnalysisLoading /> },
      { path: "/guides/explore", element: <GuideExplore /> },
      { path: "/guides/liked", element: <GuideLiked /> },
      {
        path: "/trips/:tripId/places/:tripPlaceId/purpose",
        element: <RecommendationPurpose />,
      },
      {
        path: "/trips/:tripId/places/:tripPlaceId/compare",
        element: <CompareAlternatives />,
      },
      {
        path: "/trips/:tripId/places/:tripPlaceId/preview",
        element: <ReplacementPreviewPage />,
      },
      { path: "/trips/:tripId/remaining", element: <RemainingCongested /> },
      { path: "/trips/:tripId/confirm", element: <ConfirmTrip /> },
      { path: "/trips/:tripId/saved", element: <SavedTrip /> },
      { path: "/trips/:tripId/guide", element: <Guidebook /> },
      { path: "/guide/:token", element: <SharedGuide /> },
      { path: "/mypage", element: <MyPage /> },
    ],
  },
])
