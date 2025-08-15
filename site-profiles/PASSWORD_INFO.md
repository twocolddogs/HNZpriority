# Regional Password System

## Overview
The NZ Radiology Site Profiles application includes password protection for editing functionality. Each region has its own password, and there's also an admin password that grants access to all regions.

## Development Passwords

### Regional Passwords
- **Northern Region**: `north2025`
  - Access: Auckland City Hospital, North Shore Hospital
- **Midland Region**: `mid2025`
  - Access: Waikato Hospital
- **Central Region**: `central2025`
  - Access: Wellington Hospital
- **Southern Region**: `south2025`
  - Access: Christchurch Hospital, Dunedin Hospital

### Admin Password
- **Admin Access**: `admin2025`
  - Grants editing access to ALL regions

## How It Works

1. **View Mode**: Anyone can view all site profiles without authentication
2. **Edit Mode**: Requires regional or admin password
3. **Authentication Flow**:
   - Click "Edit Mode" in hamburger menu
   - If not authenticated for current region, password prompt appears
   - Enter regional password for that region, or admin password for all regions
   - Successfully authenticated regions show checkmarks (✓) in navigation tabs
   - Authentication persists during browser session

## Visual Indicators

- **Navigation Tabs**: Authenticated regions show checkmark (✓)
- **Menu Button**: Shows authentication status
  - "Edit Mode (Authentication Required)" - Not authenticated
  - "Edit Mode (Northern ✓)" - Authenticated for current region
- **Green Text**: Authenticated menu items appear in green

## Security Notes

- **Development Only**: These are plain text passwords for development
- **Session Based**: Authentication doesn't persist across browser sessions
- **Regional Scope**: Users only need access to their specific region
- **Admin Override**: Admin password provides full access for management

## File Structure

- `regional_passwords.json` - Contains all password configuration
- Regional passwords are loaded at application startup
- No server-side validation (client-side only for development)

---
*This is a development implementation. For production, implement proper authentication with hashed passwords, server-side validation, and secure session management.*