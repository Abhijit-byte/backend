from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate user and return JWT tokens.
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {'detail': 'OPERATOR_ID and SECURITY_CIPHER required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Django auth uses username, so we'll try to find user by email
    try:
        user = User.objects.get(email=email)
        username = user.username
    except User.DoesNotExist:
        return Response(
            {'detail': 'INVALID_CREDENTIALS: Access denied'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Authenticate with username and password
    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {'detail': 'INVALID_CREDENTIALS: Access denied'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'detail': 'ACCOUNT_DISABLED: Contact system administrator'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Register a new user.
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not username or not email or not password:
        return Response(
            {'detail': 'USERNAME, EMAIL, and PASSWORD required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user exists
    if User.objects.filter(username=username).exists():
        return Response(
            {'detail': 'USERNAME_EXISTS: Choose different identifier'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {'detail': 'EMAIL_EXISTS: Account already registered'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Get current authenticated user info.
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user (token invalidation handled client-side via cookie deletion).
    """
    return Response(
        {'detail': 'SESSION_TERMINATED'},
        status=status.HTTP_200_OK
    )
