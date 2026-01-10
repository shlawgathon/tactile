package com.shlawgathon.tactile.backend.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI tactileOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Tactile CAD Analysis API")
                        .description("Long-running CAD analysis platform for DFM (Design for Manufacturing) feedback")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("Tactile Team")
                                .email("team@tactile3d.dev"))
                        .license(new License()
                                .name("MIT License")
                                .url("https://opensource.org/licenses/MIT")))
                .servers(List.of(
                        new Server().url("http://localhost:8080").description("Development Server")));
    }
}
