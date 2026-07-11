pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        // Angepasst an deine Custom Registry und bestehende Credentials
        REGISTRY = '10.111.54.64'
        REGISTRY_CREDENTIALS = 'registry-auth'
        IMAGE_NAME = 'quantum-werewolf'
        IMAGE_TAG = "${BUILD_NUMBER}"
        PYTHON_VERSION = '3.11'
        PYTEST_REPORT = 'test-results.xml'
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    echo '🔄 Checking out repository...'
                    checkout scm
                }
            }
        }

        stage('Python Tests (via Docker)') {
            steps {
                script {
                    echo '🧪 Running Setup, Linting and Tests inside Python Docker container...'
                    sh '''
                        docker run --rm \
                            -v "${WORKSPACE}:/workspace" \
                            -w /workspace \
                            python:3.11-slim \
                            bash -c "
                                echo '📦 Installing dependencies...' &&
                                pip install --upgrade pip setuptools wheel &&
                                pip install -e . &&
                                pip install -r web/server/requirements.txt pytest pytest-cov pytest-asyncio flake8 pylint &&

                                echo '🔍 Running code quality checks...' &&
                                flake8 quantumwerewolf/ web/server/ tests/ --max-line-length=120 --ignore=E501,W503 || true &&
                                pylint quantumwerewolf/ --disable=R,C --exit-zero || true &&

                                echo '🧪 Running backend tests...' &&
                                cd tests &&
                                pytest test_backend.py -v --junit-xml=../backend-test-results.xml --cov=quantumwerewolf --cov-report=html:../htmlcov_backend || true &&
                                cd .. &&

                                echo '🧪 Running web server tests...' &&
                                cd web/server &&
                                pytest tests/ -v --junit-xml=../../web-test-results.xml --cov=. --cov-report=html:../../htmlcov_web || true
                            "
                    '''
                }
            }
        }


        stage('Build Docker Image') {
            steps {
                script {
                    echo '🐳 Building Docker image...'
                    sh '''
                        # REGISTRY-Präfix hinzugefügt
                        docker build \
                            --tag ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
                            --tag ${REGISTRY}/${IMAGE_NAME}:latest \
                            --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                            --build-arg VCS_REF=$(git rev-parse --short HEAD) \
                            --build-arg VERSION=${IMAGE_TAG} \
                            -f Dockerfile .
                    '''
                }
            }
        }

        stage('Docker Image Tests') {
            steps {
                script {
                    echo '🧪 Testing Docker image...'
                    sh '''
                        # 1. Vorsorglich aufräumen (falls ein alter Build gecrasht ist)
                        docker stop quantum-werewolf-test || true
                        docker rm quantum-werewolf-test || true

                        # 2. Container im Hintergrund starten
                        docker run -d \
                            --name quantum-werewolf-test \
                            -p 8000:8000 \
                            ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

                        # Warten, bis der Container hochgefahren ist
                        sleep 5

                        # 3. Health check mit automatischem Log-Dump bei Fehler
                        echo "Running health checks..."
                        if ! curl -f http://localhost:8000/api/health; then
                            echo "❌ Health check failed! Here are the container logs:"
                            docker logs quantum-werewolf-test

                            # Cleanup vor dem Beenden des Skripts
                            docker stop quantum-werewolf-test || true
                            docker rm quantum-werewolf-test || true
                            exit 1
                        fi

                        # 4. Standard-Cleanup bei Erfolg
                        docker stop quantum-werewolf-test
                        docker rm quantum-werewolf-test
                    '''
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    echo '📤 Pushing Docker image to registry...'
                    withCredentials([usernamePassword(credentialsId: REGISTRY_CREDENTIALS, usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                        sh '''
                            echo "Logging into Docker registry..."
                            echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin ${REGISTRY}

                            docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                            docker push ${REGISTRY}/${IMAGE_NAME}:latest

                            docker logout ${REGISTRY}
                        '''
                    }
                }
            }
        }

    stage('Generate Reports') {
            steps {
                script {
                    echo '📊 Generating test reports...'
                    sh '''
                        # venv/bin/activate entfernt, da wir es nicht mehr nutzen
                        ls -la *.xml 2>/dev/null || true
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                echo '🧹 Cleaning up...'

                // Archive test results (schlägt nicht fehl, auch wenn keine XMLs da sind)
                junit allowEmptyResults: true, testResults: '**/test-results.xml,**/backend-test-results.xml,**/web-test-results.xml'

                // Die HTML Coverage Reports sind auskommentiert, bis das
                // "HTML Publisher Plugin" in Jenkins installiert wurde.
                /*
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov_backend',
                    reportFiles: 'index.html',
                    reportName: 'Backend Coverage Report'
                ])

                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov_web',
                    reportFiles: 'index.html',
                    reportName: 'Web Coverage Report'
                ])
                */

                // Clean workspace
                deleteDir()
            }
        }

        success {
            script {
                echo '✅ Pipeline completed successfully!'
            }
        }

        failure {
            script {
                echo '❌ Pipeline failed!'
            }
        }
    }
}