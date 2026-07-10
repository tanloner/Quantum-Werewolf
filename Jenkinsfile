pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        // Angepasst an deine Custom Registry und bestehende Credentials
        REGISTRY = 'docker.lsgserver.dev'
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

        stage('Setup') {
            steps {
                script {
                    echo '📦 Setting up environment...'
                    sh '''
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install --upgrade pip setuptools wheel
                    '''
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                script {
                    echo '📥 Installing dependencies...'
                    sh '''
                        . venv/bin/activate
                        pip install -e .
                        pip install -r web/server/requirements.txt
                        pip install pytest pytest-cov pytest-asyncio
                    '''
                }
            }
        }

        stage('Lint') {
            steps {
                script {
                    echo '🔍 Running code quality checks...'
                    sh '''
                        . venv/bin/activate
                        pip install pylint flake8
                        echo "Running flake8..."
                        flake8 quantumwerewolf/ web/server/ tests/ --max-line-length=120 --ignore=E501,W503 || true
                        echo "Running pylint..."
                        pylint quantumwerewolf/ --disable=R,C --exit-zero || true
                    '''
                }
            }
        }

        stage('Unit Tests - Backend') {
            steps {
                script {
                    echo '🧪 Running backend tests...'
                    sh '''
                        . venv/bin/activate
                        cd tests
                        # Report wird ins Hauptverzeichnis geschrieben
                        pytest test_backend.py -v --junit-xml=../backend-test-results.xml --cov=quantumwerewolf --cov-report=html:../htmlcov_backend || true
                    '''
                }
            }
        }

        stage('Unit Tests - Web Server') {
            steps {
                script {
                    echo '🧪 Running web server tests...'
                    sh '''
                        . venv/bin/activate
                        cd web/server
                        # Report wird ins Hauptverzeichnis geschrieben
                        pytest tests/ -v --junit-xml=../../web-test-results.xml --cov=. --cov-report=html:../../htmlcov_web || true
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
                        # Start container in background (REGISTRY-Präfix hinzugefügt)
                        docker run -d \
                            --name quantum-werewolf-test \
                            -p 8000:8000 \
                            ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

                        # Wait for container to be ready
                        sleep 5

                        # Health check
                        echo "Running health checks..."
                        curl -f http://localhost:8000/api/health || exit 1
                        curl -f http://localhost:8000/api/games/health || exit 1

                        # Cleanup
                        docker stop quantum-werewolf-test
                        docker rm quantum-werewolf-test
                    '''
                }
            }
        }

        stage('Push Docker Image') {
            when {
                branch 'main' // Ggf. auf 'master' anpassen, falls dein Branch so heißt
            }
            steps {
                script {
                    echo '📤 Pushing Docker image to registry...'
                    withCredentials([usernamePassword(credentialsId: REGISTRY_CREDENTIALS, usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                        sh '''
                            echo "Logging into Docker registry..."
                            echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin ${REGISTRY}

                            # REGISTRY-Präfix hinzugefügt
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
                        . venv/bin/activate
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

                // Archive test results
                junit allowEmptyResults: true, testResults: '**/test-results.xml,**/backend-test-results.xml,**/web-test-results.xml'

                // Archive Backend Coverage
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov_backend',
                    reportFiles: 'index.html',
                    reportName: 'Backend Coverage Report'
                ])

                // Archive Web Coverage
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov_web',
                    reportFiles: 'index.html',
                    reportName: 'Web Coverage Report'
                ])

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