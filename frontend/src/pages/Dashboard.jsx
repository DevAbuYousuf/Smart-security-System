
import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import api from "../services/api";
import "./Dashboard.css";

const SOCKET_URL = "http://localhost:5000";
const CAMERA_STREAM_URL = "http://localhost:8000/video_feed";
const CAMERA_STATS_URL = "http://localhost:8000/stats";
const BACKEND_URL = "http://localhost:5000";

const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  border: "1px solid var(--border-color, #e5e7eb)",
  borderRadius: "8px",
  background: "var(--card-bg, #ffffff)",
  color: "var(--text-color, #111827)",
  fontSize: "14px",
  outline: "none",
};

const actionButtonStyle = {
  padding: "10px 10px",
  border: "none",
  borderRadius: "8px",
  cursor: "pointer",
  fontWeight: "600",
  fontSize: "13px",
};

const Dashboard = () => {
  const [events, setEvents] = useState([]);
  const [persons, setPersons] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [socketConnected, setSocketConnected] = useState(false);
  const [liveAlert, setLiveAlert] = useState(null);
  const [cameraStatus, setCameraStatus] = useState("connecting");

  // Event Management states
  const [historyEvents, setHistoryEvents] = useState([]);
  const [historyPagination, setHistoryPagination] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [historyRefresh, setHistoryRefresh] = useState(0);

  const [historyFilters, setHistoryFilters] = useState({
    search: "",
    trackId: "",
    eventType: "",
    startDate: "",
    endDate: "",
  });

  const [historyForm, setHistoryForm] = useState({
    search: "",
    trackId: "",
    eventType: "",
    startDate: "",
    endDate: "",
  });

  const [historyPage, setHistoryPage] = useState(1);

  // Event Details Modal state
  const [selectedEvent, setSelectedEvent] = useState(null);

  const [cameraStats, setCameraStats] = useState({
    detectedPeople: 0,
    currentInside: 0,
    totalEntry: 0,
    totalExit: 0,
    livePersons: [],
  });

  // ==========================================
  // SNAPSHOT URL
  // ==========================================

  const getSnapshotUrl = (snapshot) => {
    if (!snapshot) return null;

    if (
      snapshot.startsWith("http://") ||
      snapshot.startsWith("https://")
    ) {
      return snapshot;
    }

    return `${BACKEND_URL}${snapshot.startsWith("/") ? "" : "/"}${snapshot}`;
  };

  // ==========================================
  // INITIAL DASHBOARD DATA
  // ==========================================

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError("");

      const [eventsResponse, personsResponse] = await Promise.all([
        api.get("/events"),
        api.get("/persons"),
      ]);

      if (eventsResponse.data.success) {
        setEvents(eventsResponse.data.data || []);
        setPagination(eventsResponse.data.pagination || null);
      }

      if (personsResponse.data.success) {
        setPersons(personsResponse.data.data || []);
      }
    } catch (err) {
      console.error("Dashboard API Error:", err);

      setError(
        err.response?.data?.message ||
          "Unable to connect to the backend server."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // ==========================================
  // EVENT HISTORY API + SEARCH + FILTER
  // ==========================================

  useEffect(() => {
    let isMounted = true;

    const fetchEventHistory = async () => {
      try {
        setHistoryLoading(true);
        setHistoryError("");

        const params = {
          page: historyPage,
          limit: 10,
        };

        if (historyFilters.search.trim()) {
          params.search = historyFilters.search.trim();
        }

        if (historyFilters.trackId !== "") {
          params.trackId = historyFilters.trackId;
        }

        if (historyFilters.eventType) {
          params.eventType = historyFilters.eventType;
        }

        if (historyFilters.startDate) {
          params.startDate = historyFilters.startDate;
        }

        if (historyFilters.endDate) {
          params.endDate = historyFilters.endDate;
        }

        const response = await api.get("/events", { params });

        if (!isMounted) return;

        if (response.data.success) {
          setHistoryEvents(response.data.data || []);
          setHistoryPagination(response.data.pagination || null);
        }
      } catch (err) {
        console.error("Event History Error:", err);

        if (isMounted) {
          setHistoryError(
            err.response?.data?.message ||
              "Unable to load event history."
          );
        }
      } finally {
        if (isMounted) {
          setHistoryLoading(false);
        }
      }
    };

    fetchEventHistory();

    return () => {
      isMounted = false;
    };
  }, [historyFilters, historyPage, historyRefresh]);

  // ==========================================
  // APPLY EVENT FILTERS
  // ==========================================

  const handleHistorySearch = (event) => {
    event.preventDefault();

    if (
      historyForm.startDate &&
      historyForm.endDate &&
      historyForm.startDate > historyForm.endDate
    ) {
      setHistoryError("Start date cannot be after end date.");
      return;
    }

    setHistoryPage(1);
    setHistoryFilters({ ...historyForm });
  };

  // ==========================================
  // RESET EVENT FILTERS
  // ==========================================

  const resetHistoryFilters = () => {
    const emptyFilters = {
      search: "",
      trackId: "",
      eventType: "",
      startDate: "",
      endDate: "",
    };

    setHistoryForm(emptyFilters);
    setHistoryFilters(emptyFilters);
    setHistoryPage(1);
    setHistoryError("");
  };

  // ==========================================
  // CAMERA STATISTICS
  // ==========================================

  useEffect(() => {
    let isMounted = true;

    const fetchCameraStats = async () => {
      try {
        const response = await fetch(CAMERA_STATS_URL, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(
            `Camera stats request failed: ${response.status}`
          );
        }

        const data = await response.json();

        if (isMounted) {
          setCameraStats({
            detectedPeople: data.detectedPeople ?? 0,
            currentInside: data.currentInside ?? 0,
            totalEntry: data.totalEntry ?? 0,
            totalExit: data.totalExit ?? 0,
            livePersons: Array.isArray(data.livePersons)
              ? data.livePersons
              : [],
          });
        }
      } catch (statsError) {
        console.warn(
          "Camera stats unavailable:",
          statsError.message
        );
      }
    };

    fetchCameraStats();

    const statsInterval = setInterval(fetchCameraStats, 500);

    return () => {
      isMounted = false;
      clearInterval(statsInterval);
    };
  }, []);

  // ==========================================
  // SOCKET.IO REAL-TIME CONNECTION
  // ==========================================

  useEffect(() => {
    const socket = io(SOCKET_URL);

    socket.on("connect", () => {
      console.log("Socket connected:", socket.id);
      setSocketConnected(true);
    });

    socket.on("disconnect", () => {
      console.log("Socket disconnected");
      setSocketConnected(false);
    });

    socket.on("connect_error", (err) => {
      console.error("Socket connection error:", err.message);
      setSocketConnected(false);
    });

    socket.on("security_alert", (payload) => {
      console.log("Real-time Security Alert:", payload);

      const newEvent = payload?.data;

      if (!newEvent?._id) {
        console.warn("Security alert received without event data.");
        return;
      }

      setEvents((previousEvents) => {
        const alreadyExists = previousEvents.some(
          (event) => event._id === newEvent._id
        );

        if (alreadyExists) return previousEvents;

        return [newEvent, ...previousEvents].slice(0, 10);
      });

      setPagination((previous) => {
        if (!previous) return previous;

        return {
          ...previous,
          totalEvents: previous.totalEvents + 1,
        };
      });

      setLiveAlert(newEvent);
      setHistoryRefresh((previous) => previous + 1);
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("connect_error");
      socket.off("security_alert");
      socket.disconnect();
    };
  }, []);

  // ==========================================
  // DASHBOARD STATISTICS
  // ==========================================

  const recentEntries = events.filter(
    (event) => event.eventType === "ENTRY"
  ).length;

  const recentExits = events.filter(
    (event) => event.eventType === "EXIT"
  ).length;

  const recentAlerts = events.filter(
    (event) =>
      event.eventType === "UNKNOWN_PERSON" ||
      event.status === "UNAUTHORIZED"
  ).length;

  const activePersons = persons.filter(
    (person) => person.isActive
  ).length;

  const stats = [
    {
      title: "Total Events",
      value: pagination?.totalEvents ?? 0,
      icon: "◷",
      color: "blue",
    },
    {
      title: "Recent Entries",
      value: recentEntries,
      icon: "↗",
      color: "green",
    },
    {
      title: "Recent Exits",
      value: recentExits,
      icon: "↙",
      color: "purple",
    },
    {
      title: "Active Persons",
      value: activePersons,
      icon: "♙",
      color: "orange",
    },
  ];

  // ==========================================
  // HELPER FUNCTIONS
  // ==========================================

  const formatDate = (date) => {
    if (!date) return "N/A";
    return new Date(date).toLocaleString();
  };

  const getEventClass = (type) => {
    switch (type) {
      case "ENTRY":
        return "event-entry";
      case "EXIT":
        return "event-exit";
      case "UNKNOWN_PERSON":
        return "event-unknown";
      case "AUTHORIZED_PERSON":
        return "event-authorized";
      default:
        return "";
    }
  };

  const getRecognitionClass = (status) => {
    switch (status) {
      case "AUTHORIZED":
        return "recognition-authorized";
      case "UNKNOWN":
        return "recognition-unknown";
      default:
        return "recognition-verifying";
    }
  };

  const getRecognitionLabel = (status) => {
    switch (status) {
      case "AUTHORIZED":
        return "AUTHORIZED";
      case "UNKNOWN":
        return "UNKNOWN";
      default:
        return "VERIFYING";
    }
  };

  // ==========================================
  // EVENT DETAILS MODAL FUNCTIONS
  // ==========================================

  const openEventDetails = (event) => {
    setSelectedEvent(event);
  };

  const closeEventDetails = () => {
    setSelectedEvent(null);
  };

  // ==========================================
  // REUSABLE SNAPSHOT DISPLAY
  // ==========================================

  const renderSnapshot = (snapshot, altText = "Security snapshot") => {
    const imageUrl = getSnapshotUrl(snapshot);

    if (!imageUrl) {
      return <span className="snapshot-unavailable">No Image</span>;
    }

    return (
      <a
        href={imageUrl}
        target="_blank"
        rel="noopener noreferrer"
        title="Click to view full-size snapshot"
      >
        <img
          src={imageUrl}
          alt={altText}
          className="snapshot-thumbnail"
          loading="lazy"
          onError={(event) => {
            event.currentTarget.style.display = "none";
          }}
        />
      </a>
    );
  };

  // ==========================================
  // EVENT DETAILS MODAL
  // ==========================================

  const renderEventDetailsModal = () => {
    if (!selectedEvent) return null;

    const snapshotUrl = getSnapshotUrl(selectedEvent.snapshot);

    const details = [
      {
        label: "Person Name",
        value: selectedEvent.personName || "Unknown Person",
      },
      {
        label: "Track ID",
        value:
          selectedEvent.trackId != null
            ? `#${selectedEvent.trackId}`
            : "N/A",
      },
      {
        label: "Event Type",
        value: selectedEvent.eventType?.replaceAll("_", " ") || "N/A",
      },
      {
        label: "Authorization Status",
        value: selectedEvent.status || "N/A",
      },
      {
        label: "Match Distance",
        value:
          selectedEvent.confidence != null
            ? Number(selectedEvent.confidence).toFixed(2)
            : "N/A",
      },
      {
        label: "Camera ID",
        value: selectedEvent.cameraId || "N/A",
      },
      {
        label: "Event Date & Time",
        value: formatDate(selectedEvent.eventDate),
      },
      {
        label: "Created At",
        value: formatDate(selectedEvent.createdAt),
      },
      {
        label: "Event ID",
        value: selectedEvent._id || "N/A",
      },
    ];

    return (
      <div
        onClick={closeEventDetails}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 1000,
          background: "rgba(15, 23, 42, 0.65)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "20px",
          overflowY: "auto",
        }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="event-details-title"
          onClick={(event) => event.stopPropagation()}
          style={{
            width: "100%",
            maxWidth: "700px",
            maxHeight: "90vh",
            overflowY: "auto",
            background: "#ffffff",
            borderRadius: "14px",
            padding: "24px",
            boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "15px",
              marginBottom: "20px",
            }}
          >
            <div>
              <h2
                id="event-details-title"
                style={{
                  margin: 0,
                  fontSize: "21px",
                  color: "#0f172a",
                }}
              >
                Event Details
              </h2>

              <p
                style={{
                  margin: "6px 0 0",
                  color: "#64748b",
                  fontSize: "13px",
                }}
              >
                Complete security event information
              </p>
            </div>

            <button
              type="button"
              onClick={closeEventDetails}
              aria-label="Close event details"
              style={{
                width: "35px",
                height: "35px",
                border: "none",
                borderRadius: "8px",
                background: "#f1f5f9",
                color: "#475569",
                fontSize: "20px",
                cursor: "pointer",
              }}
            >
              ×
            </button>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            {details.map((item) => (
              <div
                key={item.label}
                style={{
                  padding: "13px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "9px",
                  minWidth: 0,
                  background: "#f8fafc",
                }}
              >
                <p
                  style={{
                    margin: "0 0 7px",
                    color: "#64748b",
                    fontSize: "12px",
                    fontWeight: "600",
                  }}
                >
                  {item.label}
                </p>

                <strong
                  style={{
                    display: "block",
                    color: "#1e293b",
                    fontSize: "13px",
                    overflowWrap: "anywhere",
                  }}
                >
                  {item.value}
                </strong>
              </div>
            ))}
          </div>

          <div style={{ marginTop: "22px" }}>
            <h3
              style={{
                margin: "0 0 12px",
                color: "#0f172a",
                fontSize: "16px",
              }}
            >
              Event Snapshot
            </h3>

            {snapshotUrl ? (
              <a
                href={snapshotUrl}
                target="_blank"
                rel="noopener noreferrer"
                title="Open full-size snapshot"
              >
                <img
                  src={snapshotUrl}
                  alt="Event snapshot"
                  style={{
                    display: "block",
                    width: "100%",
                    maxHeight: "350px",
                    objectFit: "contain",
                    background: "#0f172a",
                    borderRadius: "10px",
                  }}
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                  }}
                />
              </a>
            ) : (
              <div
                style={{
                  padding: "35px 15px",
                  textAlign: "center",
                  color: "#64748b",
                  background: "#f8fafc",
                  borderRadius: "10px",
                  border: "1px dashed #cbd5e1",
                }}
              >
                No snapshot available for this event.
              </div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: "22px",
            }}
          >
            <button
              type="button"
              onClick={closeEventDetails}
              style={{
                ...actionButtonStyle,
                padding: "10px 20px",
                background: "#64748b",
                color: "#ffffff",
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ==========================================
  // DASHBOARD UI
  // ==========================================

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">🛡️</span>
          <h2>SmartGuard</h2>
        </div>

        <p className="menu-label">MAIN MENU</p>

        <nav className="menu">
          <a className="active" href="#dashboard">▦ Dashboard</a>
          <a href="#alerts">⚠ Security Alerts</a>
          <a href="#events">◷ Event History</a>
          <a href="#persons">♙ Person Management</a>
          <a href="#live-recognition">◎ Live Recognition</a>
          <a href="#faces">◎ Face Management</a>
          <a href="#camera">▣ Camera Monitoring</a>
        </nav>

        <div className="sidebar-bottom">
          <span className="online-dot"></span>
          System Online
        </div>
      </aside>

      <main className="main-content" id="dashboard">
        <header className="topbar">
          <div>
            <h1>Dashboard</h1>
            <p>Welcome to your Smart Security System</p>
          </div>

          <div className="topbar-actions">
            <div className="system-status">
              <span
                className={
                  socketConnected ? "online-dot" : "offline-dot"
                }
              ></span>
              {socketConnected ? "Live Connected" : "Live Disconnected"}
            </div>

            <button
              className="refresh-button"
              onClick={fetchDashboardData}
              disabled={loading}
            >
              ↻ Refresh
            </button>
          </div>
        </header>

        {error && <div className="error-message">{error}</div>}

        {/* LIVE SECURITY ALERT BANNER */}

        {liveAlert && (
          <div className="live-alert-banner snapshot-alert-banner">
            <div className="snapshot-alert-content">
              <div>
                <strong>⚠ New Security Alert!</strong>
                <p>
                  {liveAlert.personName || "Unknown Person"} —{" "}
                  {liveAlert.eventType?.replaceAll("_", " ")}
                </p>
                <small>{formatDate(liveAlert.eventDate)}</small>
              </div>

              {renderSnapshot(
                liveAlert.snapshot,
                "New security alert snapshot"
              )}
            </div>

            <button onClick={() => setLiveAlert(null)}>✕</button>
          </div>
        )}

        {/* MAIN STATISTICS */}

        <section className="stats-grid">
          {stats.map((stat) => (
            <div className="stat-card" key={stat.title}>
              <div className={`stat-icon ${stat.color}`}>
                {stat.icon}
              </div>

              <p>{stat.title}</p>
              <h2>{loading ? "..." : stat.value}</h2>
            </div>
          ))}
        </section>

        <section className="content-grid">
          {/* LIVE CAMERA PANEL */}

          <div className="panel camera-panel" id="camera">
            <div className="panel-header">
              <h3>Live Camera</h3>

              <span
                className={`camera-badge ${
                  cameraStatus === "connected"
                    ? "camera-connected"
                    : "camera-disconnected"
                }`}
              >
                ●{" "}
                {cameraStatus === "connected"
                  ? "Camera Connected"
                  : cameraStatus === "connecting"
                  ? "Connecting..."
                  : "Camera Disconnected"}
              </span>
            </div>

            <div className="camera-container">
              <img
                src={CAMERA_STREAM_URL}
                alt="SmartGuard Live Camera Feed"
                className="camera-video"
                onLoad={() => setCameraStatus("connected")}
                onError={() => setCameraStatus("disconnected")}
              />

              {cameraStatus !== "connected" && (
                <div className="camera-overlay">
                  <div className="camera-icon">📹</div>

                  <h3>
                    {cameraStatus === "connecting"
                      ? "Connecting to Camera..."
                      : "Camera Offline"}
                  </h3>

                  <p>
                    {cameraStatus === "connecting"
                      ? "Please wait while the camera connects."
                      : "Start the Python AI security system to view live video."}
                  </p>
                </div>
              )}
            </div>

            <div className="camera-footer">
              <span>
                <span
                  className={
                    cameraStatus === "connected"
                      ? "online-dot"
                      : "offline-dot"
                  }
                ></span>
                {cameraStatus === "connected"
                  ? "Live Streaming"
                  : "Stream Unavailable"}
              </span>

              <span>CAMERA_01</span>
            </div>

            <div
              className="camera-stats-grid"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: "12px",
                padding: "16px",
              }}
            >
              {[
                {
                  label: "Detected People",
                  value: cameraStats.detectedPeople,
                },
                {
                  label: "Current Inside",
                  value: cameraStats.currentInside,
                },
                {
                  label: "Total Entry",
                  value: cameraStats.totalEntry,
                },
                {
                  label: "Total Exit",
                  value: cameraStats.totalExit,
                },
              ].map((stat) => (
                <div
                  key={stat.label}
                  style={{
                    background: "var(--card-bg, #f4f6f9)",
                    border: "1px solid var(--border-color, #e5e7eb)",
                    borderRadius: "10px",
                    padding: "12px",
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      fontSize: "12px",
                      color: "var(--text-secondary, #6b7280)",
                    }}
                  >
                    {stat.label}
                  </p>

                  <strong
                    style={{
                      display: "block",
                      marginTop: "5px",
                      fontSize: "24px",
                    }}
                  >
                    {stat.value ?? 0}
                  </strong>
                </div>
              ))}
            </div>
          </div>

          {/* SECURITY ALERTS */}

          <div className="panel alerts-panel" id="alerts">
            <div className="panel-header">
              <h3>Recent Security Alerts</h3>

              <span className="alert-count">
                {loading ? "..." : recentAlerts}
              </span>
            </div>

            {loading ? (
              <div className="empty-state">Loading alerts...</div>
            ) : recentAlerts === 0 ? (
              <div className="empty-state">
                <span>🛡️</span>
                <p>No security alerts found</p>
              </div>
            ) : (
              <div className="alerts-list">
                {events
                  .filter(
                    (event) =>
                      event.eventType === "UNKNOWN_PERSON" ||
                      event.status === "UNAUTHORIZED"
                  )
                  .slice(0, 5)
                  .map((event) => (
                    <div
                      className="alert-item snapshot-alert-item"
                      key={event._id}
                    >
                      <span className="alert-symbol">⚠</span>

                      <div className="alert-item-details">
                        <strong>
                          {event.personName || "Unknown Person"}
                        </strong>

                        <p>
                          {event.eventType.replaceAll("_", " ")}
                        </p>

                        <small>{formatDate(event.eventDate)}</small>

                        {renderSnapshot(
                          event.snapshot,
                          `${event.personName || "Unknown Person"} snapshot`
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            )}

            <p className="section-note">
              Based on the latest {events.length} events
            </p>
          </div>
        </section>

        {/* LIVE FACE RECOGNITION */}

        <section
          className="panel live-recognition-panel"
          id="live-recognition"
        >
          <div className="panel-header">
            <div>
              <h3>Live Face Recognition</h3>
              <p className="section-note">
                Real-time AI person identification
              </p>
            </div>

            <span className="recognition-live-indicator">
              ● LIVE
            </span>
          </div>

          <div className="recognition-summary">
            <div className="recognition-summary-card">
              <span>Detected People</span>
              <strong>{cameraStats.detectedPeople}</strong>
            </div>

            <div className="recognition-summary-card">
              <span>Authorized</span>
              <strong>
                {
                  cameraStats.livePersons.filter(
                    (person) => person.status === "AUTHORIZED"
                  ).length
                }
              </strong>
            </div>

            <div className="recognition-summary-card">
              <span>Unknown</span>
              <strong>
                {
                  cameraStats.livePersons.filter(
                    (person) => person.status === "UNKNOWN"
                  ).length
                }
              </strong>
            </div>

            <div className="recognition-summary-card">
              <span>Verifying</span>
              <strong>
                {
                  cameraStats.livePersons.filter(
                    (person) => person.status === "VERIFYING"
                  ).length
                }
              </strong>
            </div>
          </div>

          {cameraStats.livePersons.length === 0 ? (
            <div className="empty-state recognition-empty">
              <span>👤</span>
              <p>No people currently detected</p>
              <small>
                Stand in front of the camera to test face recognition.
              </small>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="events-table recognition-table">
                <thead>
                  <tr>
                    <th>Track ID</th>
                    <th>Person Name</th>
                    <th>Recognition Status</th>
                    <th>Match Distance</th>
                  </tr>
                </thead>

                <tbody>
                  {cameraStats.livePersons.map((person) => (
                    <tr key={person.trackId}>
                      <td>
                        <strong>#{person.trackId}</strong>
                      </td>

                      <td>{person.name || "Unknown"}</td>

                      <td>
                        <span
                          className={`recognition-status ${getRecognitionClass(
                            person.status
                          )}`}
                        >
                          {getRecognitionLabel(person.status)}
                        </span>
                      </td>

                      <td>
                        {person.matchDistance != null
                          ? Number(person.matchDistance).toFixed(2)
                          : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* RECENT EVENTS */}

        <section className="panel events-panel">
          <div className="panel-header">
            <div>
              <h3>Recent Events</h3>

              <p className="section-note">
                Showing {events.length} recent events
              </p>
            </div>
          </div>

          {loading ? (
            <div className="empty-state">Loading events...</div>
          ) : events.length === 0 ? (
            <div className="empty-state">
              <span>📋</span>
              <p>No events available</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="events-table">
                <thead>
                  <tr>
                    <th>Person</th>
                    <th>Event Type</th>
                    <th>Status</th>
                    <th>Snapshot</th>
                    <th>Camera</th>
                    <th>Date & Time</th>
                  </tr>
                </thead>

                <tbody>
                  {events.map((event) => (
                    <tr key={event._id}>
                      <td>{event.personName || "Unknown"}</td>

                      <td>
                        <span
                          className={`event-badge ${getEventClass(
                            event.eventType
                          )}`}
                        >
                          {event.eventType.replaceAll("_", " ")}
                        </span>
                      </td>

                      <td>{event.status}</td>

                      <td>
                        {renderSnapshot(
                          event.snapshot,
                          `${event.personName || "Person"} event snapshot`
                        )}
                      </td>

                      <td>{event.cameraId}</td>
                      <td>{formatDate(event.eventDate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* =====================================
            EVENT MANAGEMENT
        ===================================== */}

        <section className="panel events-panel" id="events">
          <div className="panel-header">
            <div>
              <h3>Event Management</h3>
              <p className="section-note">
                Search, filter and manage security event history
              </p>
            </div>

            <button
              type="button"
              style={{
                ...actionButtonStyle,
                background: "#2563eb",
                color: "#ffffff",
              }}
              onClick={() => setHistoryRefresh((prev) => prev + 1)}
              disabled={historyLoading}
            >
              ↻ Refresh
            </button>
          </div>

          {/* SEARCH AND FILTER FORM */}

          <form
            onSubmit={handleHistorySearch}
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "15px",
              padding: "18px",
              marginBottom: "15px",
              background: "var(--card-bg, #f8fafc)",
              border: "1px solid var(--border-color, #e5e7eb)",
              borderRadius: "10px",
            }}
          >
            <div>
              <label
                htmlFor="history-search"
                style={{
                  display: "block",
                  marginBottom: "7px",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                Person Name
              </label>

              <input
                id="history-search"
                type="text"
                placeholder="Search name (e.g. You)"
                value={historyForm.search}
                style={inputStyle}
                onChange={(event) =>
                  setHistoryForm((prev) => ({
                    ...prev,
                    search: event.target.value,
                  }))
                }
              />
            </div>

            <div>
              <label
                htmlFor="history-track"
                style={{
                  display: "block",
                  marginBottom: "7px",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                Track ID
              </label>

              <input
                id="history-track"
                type="number"
                min="0"
                placeholder="Enter Track ID"
                value={historyForm.trackId}
                style={inputStyle}
                onChange={(event) =>
                  setHistoryForm((prev) => ({
                    ...prev,
                    trackId: event.target.value,
                  }))
                }
              />
            </div>

            <div>
              <label
                htmlFor="history-event-type"
                style={{
                  display: "block",
                  marginBottom: "7px",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                Event Type
              </label>

              <select
                id="history-event-type"
                value={historyForm.eventType}
                style={inputStyle}
                onChange={(event) =>
                  setHistoryForm((prev) => ({
                    ...prev,
                    eventType: event.target.value,
                  }))
                }
              >
                <option value="">All Event Types</option>
                <option value="ENTRY">Entry</option>
                <option value="EXIT">Exit</option>
                <option value="UNKNOWN_PERSON">Unknown Person</option>
                <option value="AUTHORIZED_PERSON">Authorized Person</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="history-start-date"
                style={{
                  display: "block",
                  marginBottom: "7px",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                Start Date
              </label>

              <input
                id="history-start-date"
                type="date"
                value={historyForm.startDate}
                style={inputStyle}
                onChange={(event) =>
                  setHistoryForm((prev) => ({
                    ...prev,
                    startDate: event.target.value,
                  }))
                }
              />
            </div>

            <div>
              <label
                htmlFor="history-end-date"
                style={{
                  display: "block",
                  marginBottom: "7px",
                  fontSize: "13px",
                  fontWeight: "600",
                }}
              >
                End Date
              </label>

              <input
                id="history-end-date"
                type="date"
                value={historyForm.endDate}
                style={inputStyle}
                onChange={(event) =>
                  setHistoryForm((prev) => ({
                    ...prev,
                    endDate: event.target.value,
                  }))
                }
              />
            </div>

            <div className="event-filter-actions">
              <button
                type="submit"
                style={{
                  ...actionButtonStyle,
                  background: "#2563eb",
                  color: "#ffffff",
                  fontSize: "13px",
                  padding: "10px 10px",
                  height: "42px",
                }}
                disabled={historyLoading}
              >
                Search / Apply
              </button>

              <button
                type="button"
                style={{
                  ...actionButtonStyle,
                  background: "#64748b",
                  color: "#ffffff",
                  fontSize: "13px",
                  padding: "10px 10px",
                  height: "42px",
                }}
                onClick={resetHistoryFilters}
              >
                Reset
              </button>
            </div>
          </form>

          {/* RESULT INFORMATION */}

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "10px",
              flexWrap: "wrap",
              marginBottom: "15px",
            }}
          >
            <p className="section-note">
              Total matching events:{" "}
              <strong>{historyPagination?.totalEvents ?? 0}</strong>
            </p>

            <p className="section-note">
              Page {historyPagination?.currentPage ?? 1} of{" "}
              {historyPagination?.totalPages ?? 0}
            </p>
          </div>

          {historyError && (
            <div className="error-message">{historyError}</div>
          )}

          {/* EVENT HISTORY TABLE */}

          {historyLoading ? (
            <div className="empty-state">
              Loading event history...
            </div>
          ) : historyEvents.length === 0 ? (
            <div className="empty-state">
              <span>📋</span>
              <p>No matching events found</p>
              <small>Try changing your search or filters.</small>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="events-table">
                <thead>
                  <tr>
                    <th>Person</th>
                    <th>Track ID</th>
                    <th>Event Type</th>
                    <th>Status</th>
                    <th>Snapshot</th>
                    <th>Camera</th>
                    <th>Date & Time</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {historyEvents.map((event) => (
                    <tr key={event._id}>
                      <td>
                        <strong>
                          {event.personName || "Unknown Person"}
                        </strong>
                      </td>

                      <td>
                        {event.trackId != null
                          ? `#${event.trackId}`
                          : "N/A"}
                      </td>

                      <td>
                        <span
                          className={`event-badge ${getEventClass(
                            event.eventType
                          )}`}
                        >
                          {event.eventType?.replaceAll("_", " ")}
                        </span>
                      </td>

                      <td>{event.status}</td>

                      <td>
                        {renderSnapshot(
                          event.snapshot,
                          `${event.personName || "Person"} event snapshot`
                        )}
                      </td>

                      <td>{event.cameraId || "N/A"}</td>

                      <td>{formatDate(event.eventDate)}</td>

                      <td>
                        <button
                          type="button"
                          onClick={() => openEventDetails(event)}
                          style={{
                            ...actionButtonStyle,
                            background: "#2563eb",
                            color: "#ffffff",
                            whiteSpace: "nowrap",
                          }}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* PAGINATION CONTROLS */}

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
              flexWrap: "wrap",
              marginTop: "20px",
            }}
          >
            <p className="section-note">
              Showing {historyEvents.length} events on this page
            </p>

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                style={{
                  ...actionButtonStyle,
                  background: historyPagination?.hasPreviousPage
                    ? "#2563eb"
                    : "#94a3b8",
                  color: "#ffffff",
                  cursor: historyPagination?.hasPreviousPage
                    ? "pointer"
                    : "not-allowed",
                }}
                disabled={
                  historyLoading ||
                  !historyPagination?.hasPreviousPage
                }
                onClick={() =>
                  setHistoryPage((prev) => Math.max(1, prev - 1))
                }
              >
                ← Previous
              </button>

              <button
                type="button"
                style={{
                  ...actionButtonStyle,
                  background: historyPagination?.hasNextPage
                    ? "#2563eb"
                    : "#94a3b8",
                  color: "#ffffff",
                  cursor: historyPagination?.hasNextPage
                    ? "pointer"
                    : "not-allowed",
                }}
                disabled={
                  historyLoading ||
                  !historyPagination?.hasNextPage
                }
                onClick={() => setHistoryPage((prev) => prev + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        </section>

        {/* REGISTERED PERSONS */}

        <section className="panel persons-panel" id="persons">
          <div className="panel-header">
            <h3>Registered Persons</h3>

            <span>
              {loading ? "..." : persons.length} Persons
            </span>
          </div>

          <div className="persons-list">
            {persons.map((person) => (
              <div className="person-item" key={person._id}>
                <div className="person-avatar">
                  {person.name?.charAt(0).toUpperCase()}
                </div>

                <div className="person-info">
                  <strong>{person.name}</strong>

                  <p>
                    {person.role} · Face Label: {person.faceLabel}
                  </p>
                </div>

                <span
                  className={
                    person.isActive ? "active-badge" : "inactive-badge"
                  }
                >
                  {person.isActive ? "Active" : "Inactive"}
                </span>
              </div>
            ))}
          </div>
        </section>

        <footer className="footer">
          SmartGuard Security System © 2026
        </footer>
      </main>

      {/* EVENT DETAILS MODAL */}

      {renderEventDetailsModal()}
    </div>
  );
};

export default Dashboard;
