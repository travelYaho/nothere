import { createBrowserRouter } from "react-router-dom"
import { MobileLayout } from "@/components/layout/MobileLayout"
import HomeGuest from "@/pages/HomeGuest"
import Login from "@/pages/Login"
import Home from "@/pages/Home"
import CompareAlternatives from "@/pages/CompareAlternatives"
import ReplacementPreviewPage from "@/pages/ReplacementPreview"
import RemainingCongested from "@/pages/RemainingCongested"
import ConfirmTrip from "@/pages/ConfirmTrip"
import Guidebook from "@/pages/Guidebook"
import SharedGuide from "@/pages/SharedGuide"

export const router = createBrowserRouter([
  {
    element: <MobileLayout />,
    children: [
      { path: "/", element: <HomeGuest /> },
      { path: "/login", element: <Login /> },
      { path: "/home", element: <Home /> },
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
    ],
  },
])
