import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  Container,
  Grid,
  TextField,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { messagingService, Recipient, MessageHistory, RecipientGroup } from '../services/messagingService';

const Messaging: React.FC = () => {
  const [message, setMessage] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<string>('');
  const [recipientGroups, setRecipientGroups] = useState<RecipientGroup[]>([]);
  const [selectedRecipients, setSelectedRecipients] = useState<Recipient[]>([]);
  const [messageHistory, setMessageHistory] = useState<MessageHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState<Date | null>(null);

  useEffect(() => {
    loadRecipientGroups();
    loadMessageHistory();
  }, []);

  const loadRecipientGroups = async () => {
    try {
      const response = await messagingService.getRecipientGroups();
      setRecipientGroups(response.data);
    } catch (err) {
      setError('Failed to load recipient groups');
    }
  };

  const loadMessageHistory = async () => {
    try {
      const response = await messagingService.getMessageHistory();
      setMessageHistory(response.data);
    } catch (err) {
      setError('Failed to load message history');
    }
  };

  const handleGroupChange = (event: React.ChangeEvent<{ value: unknown }>) => {
    const groupType = event.target.value as string;
    setSelectedGroup(groupType);
    const group = recipientGroups.find(g => g.group_type === groupType);
    setSelectedRecipients(group?.recipients || []);
  };

  const handleSendMessage = async () => {
    if (!message.trim()) {
      setError('Please enter a message');
      return;
    }

    if (selectedRecipients.length === 0) {
      setError('Please select recipients');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await messagingService.sendMessage(message, selectedRecipients, selectedGroup);
      setSuccess('Message sent successfully');
      setMessage('');
      loadMessageHistory();
    } catch (err) {
      setError('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const filteredMessageHistory = messageHistory.filter(msg => {
    if (!dateFilter) return true;
    const msgDate = new Date(msg.date_sent);
    return msgDate.toDateString() === dateFilter.toDateString();
  });

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Send Message
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Recipient Group</InputLabel>
                  <Select
                    value={selectedGroup}
                    label="Recipient Group"
                    onChange={handleGroupChange}
                  >
                    {recipientGroups.map((group) => (
                      <MenuItem key={group.group_type} value={group.group_type}>
                        {group.group_type.charAt(0).toUpperCase() + group.group_type.slice(1)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleSendMessage}
                  disabled={loading}
                >
                  {loading ? <CircularProgress size={24} /> : 'Send Message'}
                </Button>
              </Grid>

              {error && (
                <Grid item xs={12}>
                  <Alert severity="error">{error}</Alert>
                </Grid>
              )}

              {success && (
                <Grid item xs={12}>
                  <Alert severity="success">{success}</Alert>
                </Grid>
              )}
            </Grid>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Message History
            </Typography>

            <Box sx={{ mb: 2 }}>
              <DatePicker
                label="Filter by Date"
                value={dateFilter}
                onChange={(newValue) => setDateFilter(newValue)}
              />
            </Box>

            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>To</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Direction</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredMessageHistory.map((msg) => (
                    <TableRow key={msg.sid}>
                      <TableCell>
                        {new Date(msg.date_sent).toLocaleString()}
                      </TableCell>
                      <TableCell>{msg.to}</TableCell>
                      <TableCell>{msg.body}</TableCell>
                      <TableCell>
                        <Chip
                          label={msg.status}
                          color={
                            msg.status === 'delivered'
                              ? 'success'
                              : msg.status === 'failed'
                              ? 'error'
                              : 'default'
                          }
                        />
                      </TableCell>
                      <TableCell>{msg.direction}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Messaging; 