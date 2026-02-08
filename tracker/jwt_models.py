"""
Custom JWT Token models for enhanced token management and tracking.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class RefreshToken(models.Model):
    """
    Custom model to track refresh tokens for better control and auditing.
    This complements SimpleJWT's token blacklist functionality.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='refresh_tokens'
    )
    token = models.CharField(max_length=500, unique=True, db_index=True)
    jti = models.CharField(max_length=255, unique=True, db_index=True, help_text="JWT ID claim")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    is_blacklisted = models.BooleanField(default=False, db_index=True)
    blacklisted_at = models.DateTimeField(null=True, blank=True)
    
    # Device and session info
    device_info = models.CharField(max_length=255, blank=True, help_text="User agent or device info")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_blacklisted']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['jti']),
        ]
        db_table = 'jwt_refresh_tokens'
    
    def __str__(self):
        return f"Token for {self.user.username} - {self.jti[:8]}"
    
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at
    
    def blacklist(self):
        """Blacklist this token."""
        self.is_blacklisted = True
        self.blacklisted_at = timezone.now()
        self.save()
    
    def is_valid(self):
        """Check if token is valid (not expired and not blacklisted)."""
        return not self.is_expired() and not self.is_blacklisted


class AccessToken(models.Model):
    """
    Model to track access tokens for auditing and analytics.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='access_tokens'
    )
    jti = models.CharField(max_length=255, unique=True, db_index=True, help_text="JWT ID claim")
    refresh_token = models.ForeignKey(
        RefreshToken, 
        on_delete=models.CASCADE, 
        related_name='access_tokens',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Request info
    endpoint_accessed = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['jti']),
        ]
        db_table = 'jwt_access_tokens'
    
    def __str__(self):
        return f"Access Token for {self.user.username} - {self.jti[:8]}"
    
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at


class LoginSession(models.Model):
    """
    Track user login sessions for security auditing.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='login_sessions'
    )
    refresh_token = models.ForeignKey(
        RefreshToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    
    # Session info
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Device and location info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)  # mobile, desktop, tablet
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)  # city, country
    
    # Security flags
    suspicious = models.BooleanField(default=False)
    suspicious_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['login_time']),
        ]
        db_table = 'user_login_sessions'
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
    
    def logout(self):
        """Mark session as logged out."""
        self.is_active = False
        self.logout_time = timezone.now()
        self.save()
    
    def session_duration(self):
        """Get session duration in seconds."""
        if self.logout_time:
            return (self.logout_time - self.login_time).total_seconds()
        return (timezone.now() - self.login_time).total_seconds()


class UserProfile(models.Model):
    """
    Extended user profile for additional user information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Profile info
    bio = models.TextField(blank=True, max_length=500)
    avatar_url = models.URLField(blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Security settings
    two_factor_enabled = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True)
    phone_verified = models.BooleanField(default=False)
    
    # Activity tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_location = models.CharField(max_length=255, blank=True)
    login_count = models.IntegerField(default=0)
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    receive_notifications = models.BooleanField(default=True)
    receive_marketing = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def increment_login_count(self):
        """Increment login counter."""
        self.login_count += 1
        self.save()
    
    def record_failed_login(self):
        """Record failed login attempt."""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked = True
            self.locked_until = timezone.now() + timedelta(minutes=30)
        
        self.save()
    
    def reset_failed_attempts(self):
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.save()
    
    def is_locked(self):
        """Check if account is currently locked."""
        if not self.account_locked:
            return False
        
        if self.locked_until and timezone.now() > self.locked_until:
            # Auto-unlock expired locks
            self.account_locked = False
            self.locked_until = None
            self.failed_login_attempts = 0
            self.save()
            return False
        
        return True
