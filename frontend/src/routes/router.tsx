import { createBrowserRouter } from "react-router-dom"
import { MobileLayout } from "@/components/layout/MobileLayout"
import HomeGuest from "@/pages/HomeGuest"
import Login from "@/pages/Login"
import Home from "@/pages/Home"
import TripConditions from "@/pages/TripConditions"
import TripPlaces from "@/pages/TripPlaces"
import CustomPlace from "@/pages/CustomPlace"
import TripAnalysisLoading from "@/pages/TripAnalysisLoading"

export const router = createBrowserRouter([
  {
    element: <MobileLayout />,
    children: [
      { path: "/", element: <HomeGuest /> },
      { path: "/login", element: <Login /> },
      { path: "/home", element: <Home /> },
      { path: "/trips/new", element: <TripConditions /> },
      { path: "/trips/:tripId/conditions", element: <TripConditions /> },
      { path: "/trips/:tripId/places", element: <TripPlaces /> },
      { path: "/trips/:tripId/places/custom", element: <CustomPlace /> },
      { path: "/trips/:tripId/analysis", element: <TripAnalysisLoading /> },
    ],
  },
])
