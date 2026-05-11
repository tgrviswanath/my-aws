# Jenkins with Terraform + AWS CLI pre-installed
FROM jenkins/jenkins:lts-jdk17

USER root

# Install Terraform
RUN apt-get update && apt-get install -y curl unzip && \
    TERRAFORM_VERSION="1.7.0" && \
    curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
      -o terraform.zip && \
    unzip terraform.zip -d /usr/local/bin/ && \
    rm terraform.zip && \
    terraform --version

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws && \
    aws --version

# Install Docker CLI (for building images)
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/debian bullseye stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update && apt-get install -y docker-ce-cli

USER jenkins

# Pre-install plugins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
