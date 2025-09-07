# API Authentication Update - Desktop Login Implementation

## 🚀 Overview

Updated the PrimeSync application to use the new server API desktop login endpoint (`/api/desktop/login/`) instead of the previous JWT authentication system. This change implements the new authentication flow with sync_id-based login and automatic institute_id retrieval from the server response.

## 📋 Changes Summary

### 1. **Database Schema Updates**
**File**: `interfaces/database/models.py`

- **Added `sync_id` field** to Settings table for desktop login authentication
- **Modified Settings validation** to include sync_id validation
- **Updated field structure**:
  ```python
  sync_id = CharField(default="", index=True, help_text="Institute sync ID for desktop login")
  institute_id = CharField(default="", index=True, help_text="Institute ID from login response")
  ```

### 2. **API Endpoints Configuration**
**File**: `core/constants.py`

- **Added new desktop login endpoint**: `/api/desktop/login/`
- **Updated default settings** to include sync_id field
- **Maintained backward compatibility** with existing endpoints

### 3. **Authentication System Overhaul**
**File**: `services/api_auth.py`

#### **JWTTokenManager → TokenManager**
- **Simplified token management** for single token-based authentication
- **Removed complex JWT refresh logic**
- **Added institute information storage**:
  ```python
  def set_auth_token(self, token: str, institute_id: str = None, institute_name: str = None)
  def get_institute_info(self) -> Dict[str, str]
  ```

#### **New Desktop Login Authentication**
- **Implemented `authenticate_with_desktop_login()`** method:
  ```python
  def authenticate_with_desktop_login(self, url: str, username: str, password: str, sync_id: str)
  ```
- **Updated request headers** to use `Token` authentication instead of `Bearer`
- **Added automatic token regeneration** on 401 errors

### 4. **API Synchronization Updates**
**File**: `services/api_sync.py`

#### **Authentication Flow Changes**
- **Updated sync_users validation** to require sync_id instead of institute_id
- **Enhanced authentication validation** before API operations
- **Added automatic institute_id saving** to settings after successful login

#### **Connection Testing**
- **Modified `test_connection()`** to use desktop login endpoint
- **Added institute_id storage** from login response
- **Enhanced error handling** for authentication failures

### 5. **Settings Form Updates**
**File**: `interfaces/gui/dashboard_settings.py`

#### **UI Field Changes**
- **Replaced "Institute ID" with "Sync ID"** in form fields
- **Updated validation logic** to require sync_id
- **Modified form processing** to handle new field structure

#### **Enhanced User Experience**
- **Updated connection testing** to use new authentication method
- **Improved error messages** for authentication failures
- **Added proper field mapping** for sync_id and institute_id

### 6. **API Client Integration**
**File**: `services/api_client.py`

- **Updated `test_connection()`** method signature to use sync_id
- **Enhanced settings synchronization** for new authentication flow
- **Maintained existing API method compatibility**

## 🔧 Technical Implementation Details

### **Authentication Flow**

1. **User Input**: Username, Password, Sync ID (instead of Institute ID)
2. **Desktop Login**: POST to `/api/desktop/login/` with credentials
3. **Response Processing**: Extract token, user_id, institute_id, institute_name
4. **Token Storage**: Store token for subsequent API requests
5. **Institute ID Persistence**: Save institute_id to settings for future use

### **Request Authorization**

```python
# Old Format (JWT)
headers = {"Authorization": f"Bearer {access_token}"}

# New Format (Token)
headers = {"Authorization": f"Token {auth_token}"}
```

### **Error Recovery**

- **401 Unauthorized**: Automatic re-login with stored credentials
- **Token Regeneration**: Clear invalid token and obtain new one
- **Graceful Fallback**: Continue operation with fresh authentication

### **Database Migration**

The application will automatically handle the new sync_id field:
- **Existing users**: sync_id starts as empty, can be populated in settings
- **New installations**: sync_id is part of the initial setup
- **Backward compatibility**: institute_id is preserved from login response

## 📊 API Request Examples

### **Desktop Login Request**
```json
POST /api/desktop/login/
{
  "username": "your_username",
  "password": "your_password", 
  "sync_id": "institute_sync_id"
}
```

### **Desktop Login Response**
```json
{
  "token": "your_auth_token",
  "user_id": 123,
  "username": "your_username",
  "institute_id": 456,
  "institute_name": "Institute Name"
}
```

### **Authenticated API Request**
```python
headers = {
    "Content-Type": "application/json",
    "Authorization": "Token your_auth_token"
}
```

## 🔄 Migration Guide

### **For Existing Users**
1. **Update Settings**: Replace "Institute ID" with "Sync ID" in settings form
2. **Re-configure**: Enter the institute sync_id provided by your administrator
3. **Test Connection**: Verify new authentication works correctly
4. **Institute ID**: Will be automatically populated from server response

### **For New Installations**
1. **Initial Setup**: Configure Cloud API URL, Username, Password, and Sync ID
2. **Authentication**: System will automatically obtain institute_id on first login
3. **Normal Operation**: All subsequent operations use the stored authentication

## ✅ Validation and Testing

### **Connection Testing**
- **Enhanced test flow**: Validates desktop login authentication
- **Institute info verification**: Confirms API access with obtained institute_id
- **Error handling**: Clear feedback for authentication failures

### **Error Scenarios Handled**
1. **Invalid Credentials**: Clear error message with authentication failure
2. **Invalid Sync ID**: Server-side validation with appropriate error response
3. **Network Issues**: Proper timeout and retry handling
4. **Token Expiration**: Automatic re-authentication with stored credentials

## 🎯 Benefits

### **Security Improvements**
- **Simplified authentication**: Single token-based system
- **Automatic institute validation**: Server determines institute access
- **Credential validation**: Enhanced server-side credential checking

### **User Experience**
- **Clearer configuration**: Sync ID concept is more intuitive than Institute ID
- **Automatic setup**: Institute ID populated automatically
- **Better error messages**: Specific feedback for authentication issues

### **Operational Benefits**
- **Server-controlled access**: Centralized institute assignment
- **Simplified deployment**: Users only need sync_id, not institute_id
- **Enhanced logging**: Better tracking of authentication events

## 🔧 Files Modified

1. **`interfaces/database/models.py`** - Added sync_id field to Settings
2. **`core/constants.py`** - Added desktop login endpoint and updated defaults
3. **`services/api_auth.py`** - Complete authentication system overhaul
4. **`services/api_sync.py`** - Updated for new authentication flow
5. **`services/api_client.py`** - Updated method signatures
6. **`interfaces/gui/dashboard_settings.py`** - Updated settings form UI

## 🚀 Next Steps

### **For Development**
1. **Database Migration**: Existing databases will automatically add sync_id field
2. **Settings Update**: Users need to configure sync_id in place of institute_id
3. **Testing**: Verify authentication works with new endpoint

### **For Deployment**
1. **Server Configuration**: Ensure `/api/desktop/login/` endpoint is available
2. **User Training**: Update documentation to reflect sync_id usage
3. **Monitoring**: Watch for authentication-related issues during transition

---

**Date Implemented**: September 8, 2025  
**Compatibility**: Maintains backward compatibility with existing data  
**API Version**: Updated for new desktop login authentication  
**Status**: ✅ Ready for testing and deployment