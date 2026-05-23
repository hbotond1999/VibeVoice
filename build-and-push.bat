@echo off
REM VibeVoice vLLM ASR - Docker Build and Push Script
REM Builds and pushes the OpenShift-compatible image

echo.
echo ============================================================
echo   VibeVoice vLLM ASR - Docker Build and Push
echo ============================================================
echo.

set IMAGE_NAME=docker-releases.barre.hu/iqcc/vllm-vibevoice-asr
set IMAGE_TAG=v5
set FULL_IMAGE=%IMAGE_NAME%:%IMAGE_TAG%

echo Building Docker image...
echo Image: %FULL_IMAGE%
echo.

docker build -f Dockerfile.openshift -t %FULL_IMAGE% .
if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed!
    exit /b %ERRORLEVEL%
)

echo.
echo Build successful!
echo.
echo Pushing image to registry...
echo.

docker push %FULL_IMAGE%
if %ERRORLEVEL% neq 0 (
    echo.
    echo Push failed!
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================================
echo   Successfully built and pushed!
echo   Image: %FULL_IMAGE%
echo ============================================================
echo.
