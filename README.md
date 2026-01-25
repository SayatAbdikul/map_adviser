# Map Adviser 🗺️

An AI-powered route planning and location-sharing application that helps users find optimal routes using natural language queries. Built with a FastAPI backend, React frontend, and integrated with 2GIS mapping services and Google Gemini AI.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![React](https://img.shields.io/badge/react-19.x-61dafb.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.x-3178c6.svg)

## 🌟 Features

### 🤖 AI-Powered Route Planning
- **Natural Language Queries**: Simply describe where you want to go in plain language (Russian or English)
- **Smart Route Optimization**: AI automatically decides whether to optimize for time or distance based on context
- **Multiple Route Variants**: Get 3 different route options with varying trade-offs
- **Category-Based Stops**: Request stops at places by category (e.g., "bank", "cafe", "pharmacy") and the AI finds optimal locations

### 🚗 Multi-Modal Transportation
- **Driving Routes**: Car navigation with turn-by-turn directions
- **Walking Routes**: Pedestrian-friendly paths
- **Public Transport**: 
  - Metro, bus, tram, trolleybus support
  - Detailed transfer information
  - Walking segments between stops
  - Real-time schedule integration

### 👥 Real-Time Collaboration (Rooms)
- **Create/Join Rooms**: Share a room code with friends
- **Live Location Sharing**: See all room members on the map in real-time
- **Meeting Place Finder**: AI finds the optimal meeting point that minimizes travel time for all members
- **Room Chat**: Integrated chat with AI assistant for group route planning

### 🔐 Authentication
- User registration and login
- JWT-based authentication
- Secure password hashing with bcrypt
- Supabase integration for user storage

### 🗺️ Interactive Map
- 2GIS MapGL integration
- Route visualization with colored polylines
- Waypoint markers
- Member location markers with real-time updates
- Manual location mode for testing

---

## 🏗️ Architecture

```
map_adviser/
├── core/                    # Backend (FastAPI)
│   ├── agent/              # AI Agent System
│   │   ├── path_agent.py   # Main route planning agent
│   │   ├── room_chat_agent.py  # Room collaboration agent
│   │   └── tools/          # Agent tools for API interaction
│   ├── services/           # 2GIS API clients
│   ├── models/             # Pydantic schemas
│   ├── main.py            # FastAPI application
│   └── room_manager.py    # WebSocket room management
│
├── front/                  # Frontend (React + TypeScript)
│   └── src/
│       ├── components/    # React components
│       ├── store/         # Zustand state management
│       ├── services/      # API service layers
│       └── types/         # TypeScript type definitions
│
├── routing/               # Legacy routing service (deprecated)
├── public_transport_experiments/
├── regions_experiments/
└── search_experiments/
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **npm or yarn**

### API Keys Required

| Service | Key | Description |
|---------|-----|-------------|
| 2GIS | `GIS_API_KEY` | Places, routing, and public transport APIs |
| Google Gemini | `GEMINI_API_KEY` | AI model for natural language processing |
| Supabase | `SUPABASE_URL`, `SUPABASE_ANON_KEY` | User authentication and storage |

### Backend Setup

```bash
# Navigate to core directory
cd core

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
# Navigate to front directory
cd front

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 📡 API Reference

### Route Planning

#### `POST /route`
Plan an optimal route based on natural language request.

**Request Body:**
```json
{
  "query": "Поехать от Назарбаев Университета до банка, потом в кафе, потом в Ботанический парк",
  "mode": "driving"  // "driving" | "walking" | "public_transport"
}
```

**Response:**
```json
{
  "request_summary": {
    "origin_address": "Nazarbayev University",
    "intent": "Route with stops at bank and cafe",
    "transport_mode": "driving",
    "optimization_choice": "distance"
  },
  "routes": [
    {
      "route_id": 1,
      "title": "Fastest Route",
      "total_distance_meters": 15420,
      "total_duration_minutes": 28.5,
      "waypoints": [...],
      "route_geometry": [[lon, lat], ...],
      "directions": [...]
    }
  ]
}
```

### Room Management

#### `POST /api/rooms`
Create a new collaboration room.

#### `GET /api/rooms/{code}`
Get room information by code.

#### `WebSocket /ws/room/{code}`
Real-time room synchronization.

**Message Types (Client → Server):**
- `location`: Update member location
- `heartbeat`: Keep connection alive
- `room_chat`: Send chat message to AI

**Message Types (Server → Client):**
- `room_state`: Full room state on join
- `member_joined`: New member notification
- `member_left`: Member departure notification
- `location_update`: Location broadcast
- `chat_message`: Chat message (user or AI)
- `agent_typing`: AI typing indicator

### Authentication

#### `POST /auth/register`
Register a new user.

#### `POST /auth/login`
Login and receive JWT token.

#### `GET /auth/me`
Get current user information.

---

## 🛠️ AI Agent System

The core intelligence of Map Adviser is built using LiteLLM with Google Gemini, implementing a tool-based agent architecture.

### Available Tools

| Tool | Description |
|------|-------------|
| `geocode_address` | Convert addresses to coordinates |
| `search_nearby_places` | Find places by category near a location |
| `find_optimal_place` | Find place that minimizes route detour |
| `calculate_route` | Get driving/walking route between points |
| `calculate_public_transport_route` | Get transit directions |
| `search_region` | Find region IDs for city-specific searches |
| `find_meeting_place` | Find optimal meeting point for group |

### Agent Workflow

1. **Query Analysis**: Parse natural language to identify origin, destination, and waypoints
2. **Region Detection**: If city mentioned, get region ID for localized search
3. **Location Resolution**: Geocode addresses and find places by category
4. **Route Calculation**: Calculate optimal routes with specified mode
5. **Response Formatting**: Structure response with multiple route variants

---

## 🎨 Frontend Architecture

### State Management (Zustand)

| Store | Purpose |
|-------|---------|
| `useAuthStore` | Authentication state and actions |
| `useMapStore` | Map instance and viewport |
| `useRouteStore` | Route data and selection |
| `useRoomStore` | Room state and WebSocket |
| `useChatStore` | Chat messages and UI state |
| `useThemeStore` | Theme preferences |

### Key Components

```
components/
├── auth/          # Login, Register, ProtectedRoute
├── chat/          # ChatDrawer, ChatInput, MessageList
├── map/           # MapContainer, MapControls, MapMarkers
├── room/          # RoomPanel, MemberMarkers, RoomChat
├── route/         # RouteDetailsPanel, RouteCard
├── search/        # SearchBar
└── layout/        # AppShell, MainLayout
```

---

## 🔧 Configuration

### Backend Environment Variables

```env
# AI Configuration
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini/gemini-2.5-flash  # Optional

# 2GIS API
GIS_API_KEY=your_2gis_api_key

# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

# JWT Settings
JWT_SECRET=your_jwt_secret_change_me
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Frontend Environment Variables

```env
VITE_2GIS_API_KEY=your_2gis_api_key
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

---

## 🌐 2GIS API Integration

Map Adviser integrates with multiple 2GIS APIs:

### Places/Catalog API
- Geocoding addresses
- Searching places by category
- POI information and ratings

### Routing API
- Car and pedestrian routing
- Turn-by-turn directions
- Route geometry for map display

### Public Transport API
- Multi-modal transit routing
- Transfer information
- Walking segments
- Line colors and names

### Regions API
- City/region lookup
- Region-scoped searches
- Location validation

---

## 📱 Usage Examples

### Basic Route Planning
```
"Поехать от Красной Площади до банка, потом в кафе, потом в Парк Горького"
```
The AI will:
1. Geocode "Red Square" as origin
2. Find an optimal bank along the route
3. Find a cafe near the bank
4. Geocode "Gorky Park" as destination
5. Return 3 route variants

### Time-Based Planning
```
"Когда выехать, чтобы быть на работе к 9:00?"
```
The AI calculates departure time based on estimated travel duration.

### Public Transport
```
"Как доехать на общественном транспорте от станции Комсомольская до ВДНХ"
```
Returns transit options with metro, bus, and walking segments.

### Group Meeting
In a room chat:
```
"Найди кафе для встречи"
```
The AI calculates the centroid of all member locations and finds the best meeting place.

---

## 🧪 Development

### Running Tests
```bash
cd routing
pytest tests/
```

### Code Style
```bash
# Frontend
cd front
npm run lint
npm run format

# Type checking
npm run type-check
```

### Building for Production
```bash
# Frontend
cd front
npm run build
```

---

## 📂 Project Structure Details

### Backend (`/core`)

| File/Directory | Description |
|----------------|-------------|
| `main.py` | FastAPI application entry point |
| `auth_endpoints.py` | Authentication API routes |
| `auth_service.py` | Password hashing utilities |
| `jwt_handler.py` | JWT token creation/validation |
| `room_manager.py` | WebSocket room management |
| `supabase_client.py` | Supabase client singleton |
| `agent/` | AI agent implementation |
| `services/` | 2GIS API clients |
| `models/` | Pydantic schemas |

### Frontend (`/front`)

| Directory | Description |
|-----------|-------------|
| `components/` | React UI components |
| `store/` | Zustand state stores |
| `services/` | API service functions |
| `types/` | TypeScript definitions |
| `hooks/` | Custom React hooks |
| `pages/` | Page components |
| `constants/` | App configuration |

---

## 🔒 Security Considerations

- JWT tokens for API authentication
- Passwords hashed with bcrypt
- CORS configured for allowed origins
- Environment variables for secrets
- Supabase Row Level Security recommended

---

## 🚧 Known Limitations

1. **Region Coverage**: Only regions supported by 2GIS
2. **Rate Limits**: 2GIS API has rate limiting (handled with backoff)
3. **Real-time Accuracy**: Location updates depend on client GPS
4. **Language**: AI prompts optimized for Russian queries

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- [2GIS](https://2gis.com/) for mapping and routing APIs
- [Google Gemini](https://deepmind.google/technologies/gemini/) for AI capabilities
- [Supabase](https://supabase.com/) for authentication
- [React](https://react.dev/) and [Vite](https://vitejs.dev/) for frontend tooling

---

## 📞 Support

For questions or issues, please open a GitHub issue or contact the maintainers.
