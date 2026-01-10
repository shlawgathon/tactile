package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.service.FileStorageService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Map;

@RestController
@RequestMapping("/api/files")
@Tag(name = "Files", description = "File Upload and Download")
public class FileController {

    private final FileStorageService fileStorageService;

    public FileController(FileStorageService fileStorageService) {
        this.fileStorageService = fileStorageService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "Upload file", description = "Upload a STEP/CAD file for analysis")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "File uploaded successfully"),
            @ApiResponse(responseCode = "400", description = "Invalid file")
    })
    public ResponseEntity<Map<String, String>> uploadFile(
            @Parameter(description = "STEP/CAD file to upload") @RequestParam("file") MultipartFile file) {

        try {
            String fileId = fileStorageService.uploadFile(file);
            return ResponseEntity.ok(Map.of(
                    "fileId", fileId,
                    "filename", file.getOriginalFilename(),
                    "size", String.valueOf(file.getSize())));
        } catch (IOException e) {
            return ResponseEntity.badRequest().body(Map.of("error", "Failed to upload file"));
        }
    }

    @GetMapping("/{fileId}")
    @Operation(summary = "Download file", description = "Download a file by ID")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "File downloaded"),
            @ApiResponse(responseCode = "404", description = "File not found")
    })
    public ResponseEntity<InputStreamResource> downloadFile(
            @Parameter(description = "File ID") @PathVariable String fileId) {

        try {
            var resource = fileStorageService.downloadFile(fileId);

            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION,
                            "attachment; filename=\"" + resource.getFilename() + "\"")
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .body(new InputStreamResource(resource.getInputStream()));
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{fileId}")
    @Operation(summary = "Delete file", description = "Delete a file by ID")
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "File deleted"),
            @ApiResponse(responseCode = "404", description = "File not found")
    })
    public ResponseEntity<Void> deleteFile(
            @Parameter(description = "File ID") @PathVariable String fileId) {

        try {
            fileStorageService.deleteFile(fileId);
            return ResponseEntity.noContent().build();
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }
}
