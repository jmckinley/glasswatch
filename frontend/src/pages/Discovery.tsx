/**
 * Asset Discovery Dashboard
 * 
 * Manage and trigger asset discovery scans across cloud providers,
 * containers, Kubernetes, network, and CMDB sources.
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Checkbox,
  TextField,
  Switch,
  Select,
  MenuItem
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CloudQueue as CloudIcon,
  Storage as StorageIcon,
  Router as NetworkIcon,
  Security as SecurityIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { discoveryApi } from '../services/api';

interface Scanner {
  name: string;
  type: string;
  available: boolean;
  description: string;
  requires?: string[];
  error?: string;
}

interface DiscoveryStatus {
  status: string;
  started_at?: string;
  completed_at?: string;
  summary?: {
    assets_discovered: number;
    assets_created: number;
    assets_updated: number;
    total_errors: number;
    scanner_results: Array<{
      scanner: string;
      assets: number;
      duration: number;
      errors: number;
    }>;
  };
}

interface AutoSyncConfig {
  enabled: boolean;
  scanners: string[];
  schedule: {
    type: 'interval' | 'cron';
    interval_hours?: number;
    cron_expr?: string;
  };
  next_run?: string;
}

export default function DiscoveryPage() {
  const [scanners, setScanners] = useState<Scanner[]>([]);
  const [selectedScanners, setSelectedScanners] = useState<string[]>([]);
  const [status, setStatus] = useState<DiscoveryStatus | null>(null);
  const [autoSync, setAutoSync] = useState<AutoSyncConfig>({
    enabled: false,
    scanners: [],
    schedule: { type: 'interval', interval_hours: 24 }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadScanners();
    loadStatus();
    loadAutoSyncStatus();
  }, []);

  const loadScanners = async () => {
    try {
      const data = await discoveryApi.listScanners();
      setScanners(data.scanners);
      
      // Auto-select available scanners
      const available = data.scanners
        .filter((s: Scanner) => s.available)
        .map((s: Scanner) => s.name);
      setSelectedScanners(available);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const loadStatus = async () => {
    try {
      const data = await discoveryApi.getStatus();
      setStatus(data);
    } catch (err: any) {
      // Ignore if no scans yet
      if (!err.message.includes('no_scan')) {
        console.error('Failed to load status:', err);
      }
    }
  };

  const loadAutoSyncStatus = async () => {
    try {
      const data = await discoveryApi.getAutoSyncStatus();
      setAutoSync(data);
    } catch (err: any) {
      console.error('Failed to load auto-sync status:', err);
    }
  };

  const triggerScan = async () => {
    if (selectedScanners.length === 0) {
      setError('Please select at least one scanner');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await discoveryApi.triggerScan({
        scanners: selectedScanners,
        parallel: true,
        update_existing: true
      });

      // Poll for status
      const interval = setInterval(async () => {
        const data = await discoveryApi.getStatus();
        setStatus(data);

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
        }
      }, 5000);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const configureAutoSync = async () => {
    try {
      await discoveryApi.configureAutoSync(autoSync);
      loadAutoSyncStatus();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const toggleScanner = (name: string) => {
    setSelectedScanners(prev =>
      prev.includes(name)
        ? prev.filter(s => s !== name)
        : [...prev, name]
    );
  };

  const groupedScanners = scanners.reduce((acc, scanner) => {
    if (!acc[scanner.type]) {
      acc[scanner.type] = [];
    }
    acc[scanner.type].push(scanner);
    return acc;
  }, {} as Record<string, Scanner[]>);

  const typeIcons: Record<string, React.ReactElement> = {
    cloud: <CloudIcon />,
    container: <StorageIcon />,
    kubernetes: <SecurityIcon />,
    network: <NetworkIcon />,
    cmdb: <StorageIcon />
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Asset Discovery
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Scanners Selection */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Available Scanners
              </Typography>

              {Object.entries(groupedScanners).map(([type, typeScannersArr]) => (
                <Accordion key={type} defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {typeIcons[type]}
                      <Typography sx={{ textTransform: 'capitalize' }}>
                        {type} ({typeScannersArr.length})
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <FormGroup>
                      {typeScannersArr.map(scanner => (
                        <Box key={scanner.name} sx={{ mb: 1 }}>
                          <FormControlLabel
                            control={
                              <Checkbox
                                checked={selectedScanners.includes(scanner.name)}
                                onChange={() => toggleScanner(scanner.name)}
                                disabled={!scanner.available || loading}
                              />
                            }
                            label={
                              <Box>
                                <Typography variant="body2">
                                  {scanner.name}
                                  {!scanner.available && (
                                    <Chip
                                      label="Not Available"
                                      size="small"
                                      color="warning"
                                      sx={{ ml: 1 }}
                                    />
                                  )}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {scanner.description}
                                </Typography>
                                {scanner.error && (
                                  <Typography variant="caption" color="error" display="block">
                                    {scanner.error}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        </Box>
                      ))}
                    </FormGroup>
                  </AccordionDetails>
                </Accordion>
              ))}

              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
                  onClick={triggerScan}
                  disabled={loading || selectedScanners.length === 0}
                  fullWidth
                >
                  {loading ? 'Scanning...' : `Scan with ${selectedScanners.length} Scanners`}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Status & Auto-Sync */}
        <Grid item xs={12} md={6}>
          {/* Current Status */}
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Scan Status
              </Typography>

              {status ? (
                <>
                  <Chip
                    label={status.status}
                    color={
                      status.status === 'completed' ? 'success' :
                      status.status === 'running' ? 'primary' :
                      'error'
                    }
                    sx={{ mb: 2 }}
                  />

                  {status.summary && (
                    <Box>
                      <Typography variant="body2">
                        Assets Discovered: {status.summary.assets_discovered}
                      </Typography>
                      <Typography variant="body2">
                        Created: {status.summary.assets_created}
                      </Typography>
                      <Typography variant="body2">
                        Updated: {status.summary.assets_updated}
                      </Typography>
                      {status.summary.total_errors > 0 && (
                        <Typography variant="body2" color="error">
                          Errors: {status.summary.total_errors}
                        </Typography>
                      )}
                    </Box>
                  )}

                  {status.started_at && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                      Started: {new Date(status.started_at).toLocaleString()}
                    </Typography>
                  )}
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No scans run yet
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Auto-Sync Configuration */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">
                  Auto-Sync
                </Typography>
                <ScheduleIcon />
              </Box>

              <FormControlLabel
                control={
                  <Switch
                    checked={autoSync.enabled}
                    onChange={(e) => setAutoSync({ ...autoSync, enabled: e.target.checked })}
                  />
                }
                label="Enable Automatic Discovery"
              />

              {autoSync.enabled && (
                <Box sx={{ mt: 2 }}>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <FormLabel>Schedule Type</FormLabel>
                    <Select
                      value={autoSync.schedule.type}
                      onChange={(e) => setAutoSync({
                        ...autoSync,
                        schedule: { ...autoSync.schedule, type: e.target.value as 'interval' | 'cron' }
                      })}
                    >
                      <MenuItem value="interval">Interval</MenuItem>
                      <MenuItem value="cron">Cron Expression</MenuItem>
                    </Select>
                  </FormControl>

                  {autoSync.schedule.type === 'interval' ? (
                    <TextField
                      label="Interval (hours)"
                      type="number"
                      value={autoSync.schedule.interval_hours || 24}
                      onChange={(e) => setAutoSync({
                        ...autoSync,
                        schedule: { ...autoSync.schedule, interval_hours: parseInt(e.target.value) }
                      })}
                      fullWidth
                      InputProps={{ inputProps: { min: 1 } }}
                    />
                  ) : (
                    <TextField
                      label="Cron Expression"
                      value={autoSync.schedule.cron_expr || ''}
                      onChange={(e) => setAutoSync({
                        ...autoSync,
                        schedule: { ...autoSync.schedule, cron_expr: e.target.value }
                      })}
                      fullWidth
                      placeholder="0 0 * * *"
                      helperText="Example: 0 0 * * * (daily at midnight)"
                    />
                  )}

                  {autoSync.next_run && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                      Next run: {new Date(autoSync.next_run).toLocaleString()}
                    </Typography>
                  )}

                  <Button
                    variant="outlined"
                    onClick={configureAutoSync}
                    fullWidth
                    sx={{ mt: 2 }}
                  >
                    Save Auto-Sync Configuration
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
