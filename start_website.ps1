# Start Docker Desktop if Docker is not running
docker info *> $null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
}

# Wait until Docker is ready
Write-Host "Waiting for Docker..."
do {
    Start-Sleep -Seconds 3
    docker info *> $null
} until ($LASTEXITCODE -eq 0)

# Start Piston if it is stopped
docker start piston | Out-Null

# Start AI Code Reviewer
Write-Host "Starting AI Code Reviewer..."
python -m streamlit run app.py