package com.shlawgathon.tactile.backend.service;

import com.shlawgathon.tactile.backend.BaseE2ETest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;

import static org.junit.jupiter.api.Assertions.*;

class FileStorageServiceE2ETest extends BaseE2ETest {

    @Autowired
    private FileStorageService fileStorageService;

    @Test
    void shouldUploadAndDownloadFile() throws Exception {
        // Given
        byte[] content = "test step file content".getBytes();
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "test.step",
                "application/step",
                content);

        // When
        String fileId = fileStorageService.uploadFile(file);

        // Then
        assertNotNull(fileId);

        // Download and verify
        var resource = fileStorageService.downloadFile(fileId);
        assertNotNull(resource);
        assertEquals("test.step", resource.getFilename());
    }

    @Test
    void shouldUploadBase64Content() {
        // Given
        String base64Content = java.util.Base64.getEncoder().encodeToString("test content".getBytes());

        // When
        String fileId = fileStorageService.uploadBase64(
                base64Content,
                "base64-file.step",
                "application/step");

        // Then
        assertNotNull(fileId);
    }

    @Test
    void shouldDeleteFile() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "delete-me.step",
                "application/step",
                "content to delete".getBytes());
        String fileId = fileStorageService.uploadFile(file);

        // When
        fileStorageService.deleteFile(fileId);

        // Then
        assertThrows(RuntimeException.class, () -> fileStorageService.downloadFile(fileId));
    }

    @Test
    void shouldGenerateFileUrl() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "url-test.step",
                "application/step",
                "url test content".getBytes());
        String fileId = fileStorageService.uploadFile(file);

        // When
        String url = fileStorageService.getFileUrl(fileId);

        // Then
        assertNotNull(url);
        assertTrue(url.contains(fileId));
    }
}
