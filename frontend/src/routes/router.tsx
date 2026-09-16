import { createBrowserRouter } from "react-router-dom"
import { MobileLayout } from "@/components/layout/MobileLayout"
import HomeGuest from "@/pages/HomeGuest"
import Login from "@/pages/Login"
import Home from "@/pages/Home"
import Bookmarks from "@/pages/Bookmarks"
import TripConditions from "@/pages/TripConditions"
import TripPlaces from "@/pages/TripPlaces"
import CustomPlace from "@/pages/CustomPlace"
import TripPurpose from "@/pages/TripPurpose"
import TripAnalysisLoading from "@/pages/TripAnalysisLoading"
import GuideExplore from "@/pages/GuideExplore"
import GuideLiked from "@/pages/GuideLiked"
import CompareAlternatives from "@/pages/CompareAlternatives"
import RecommendationPurpose from "@/pages/RecommendationPurpose"
import ReplacementPreviewPage from "@/pages/ReplacementPreview"
import RemainingCongested from "@/pages/RemainingCongested"
import ConfirmTrip from "@/pages/ConfirmTrip"
import Guidebook from "@/pages/Guidebook"
import SharedGuide from "@/pages/SharedGuide"
import MyPage from "@/pages/MyPage"

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
      { path: "/trips/:tripId/purpose", element: <TripPurpose /> },
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
      { path: "/trips/:tripId/guide", element: <Guidebook /> },
      { path: "/guide/:token", element: <SharedGuide /> },
      { path: "/mypage", element: <MyPage /> },
    ],
  },
])
