FROM ghcr.io/graalvm/jdk-community:21
COPY /image /app
WORKDIR /app
CMD ["java", "-Xms1G", "-Xmx2G", "-jar", "backend-0.0.1-SNAPSHOT.jar"]
