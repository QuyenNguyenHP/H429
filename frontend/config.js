window.APP_CONFIG = {
  apiBaseUrl: `${window.location.protocol}//${window.location.hostname}:8131`,
  refreshMs: 5000,
  paths: {
    analog: "/api/live/analog_lable_value",
    timestamp: "/api/live/timestamp",
  },
};
