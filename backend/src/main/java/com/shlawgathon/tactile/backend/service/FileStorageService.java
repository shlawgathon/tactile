package com.shlawgathon.tactile.backend.service;

import com.mongodb.client.gridfs.GridFSBucket;
import com.mongodb.client.gridfs.model.GridFSUploadOptions;
import org.bson.Document;
import org.bson.types.ObjectId;
import org.springframework.data.mongodb.gridfs.GridFsResource;
import org.springframework.data.mongodb.gridfs.GridFsTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Base64;

@Service
public class FileStorageService {

    private final GridFsTemplate gridFsTemplate;
    private final GridFSBucket gridFSBucket;

    public FileStorageService(GridFsTemplate gridFsTemplate, GridFSBucket gridFSBucket) {
        this.gridFsTemplate = gridFsTemplate;
        this.gridFSBucket = gridFSBucket;
    }

    /**
     * Upload a file from MultipartFile.
     */
    public String uploadFile(MultipartFile file) throws IOException {
        Document metadata = new Document();
        metadata.put("contentType", file.getContentType());
        metadata.put("originalFilename", file.getOriginalFilename());

        ObjectId fileId = gridFsTemplate.store(
                file.getInputStream(),
                file.getOriginalFilename(),
                file.getContentType(),
                metadata);

        return fileId.toString();
    }

    /**
     * Upload a file from base64 encoded string.
     */
    public String uploadBase64(String base64Content, String filename, String contentType) {
        byte[] data = Base64.getDecoder().decode(base64Content);

        Document metadata = new Document();
        metadata.put("contentType", contentType);
        metadata.put("originalFilename", filename);

        GridFSUploadOptions options = new GridFSUploadOptions()
                .metadata(metadata);

        ObjectId fileId = gridFSBucket.uploadFromStream(
                filename,
                new ByteArrayInputStream(data),
                options);

        return fileId.toString();
    }

    /**
     * Download a file by ID.
     */
    public GridFsResource downloadFile(String fileId) {
        var file = gridFsTemplate.findOne(
                new org.springframework.data.mongodb.core.query.Query(
                        org.springframework.data.mongodb.core.query.Criteria.where("_id").is(new ObjectId(fileId))));

        if (file == null) {
            throw new RuntimeException("File not found: " + fileId);
        }

        return gridFsTemplate.getResource(file);
    }

    /**
     * Get file as InputStream.
     */
    public InputStream getFileStream(String fileId) {
        return gridFSBucket.openDownloadStream(new ObjectId(fileId));
    }

    /**
     * Delete a file by ID.
     */
    public void deleteFile(String fileId) {
        gridFSBucket.delete(new ObjectId(fileId));
    }

    /**
     * Generate a download URL for the file.
     */
    public String getFileUrl(String fileId) {
        return "/api/files/" + fileId;
    }
}
