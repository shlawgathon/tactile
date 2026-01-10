package com.shlawgathon.tactile.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.shlawgathon.tactile.backend.dto.PaymentRequirement;
import com.shlawgathon.tactile.backend.model.SubscriptionTier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Service for x402 payment protocol integration with CDP Facilitator API.
 */
@Service
public class X402Service {

    private static final Logger log = LoggerFactory.getLogger(X402Service.class);

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    @Value("${cdp.api.url}")
    private String cdpApiUrl;

    @Value("${cdp.api.key-name}")
    private String cdpKeyName;

    @Value("${cdp.api.key-secret}")
    private String cdpKeySecret;

    @Value("${cdp.x402.pay-to-address}")
    private String payToAddress;

    @Value("${cdp.x402.network}")
    private String network;

    @Value("${cdp.x402.asset}")
    private String asset;

    @Value("${cdp.x402.prices.pro}")
    private String proPriceUsd;

    @Value("${cdp.x402.prices.enterprise}")
    private String enterprisePriceUsd;

    public X402Service(ObjectMapper objectMapper) {
        this.httpClient = HttpClient.newHttpClient();
        this.objectMapper = objectMapper;
    }

    /**
     * Build the payment requirement for a given target tier.
     */
    public PaymentRequirement buildPaymentRequirement(SubscriptionTier targetTier) {
        String price = switch (targetTier) {
            case PRO -> "$" + proPriceUsd;
            case ENTERPRISE -> "$" + enterprisePriceUsd;
            default -> throw new IllegalArgumentException("Cannot upgrade to FREE tier");
        };

        return PaymentRequirement.builder()
                .scheme("exact")
                .network(network)
                .price(price)
                .payTo(payToAddress)
                .asset(asset)
                .description("Upgrade to " + targetTier.name() + " tier")
                .build();
    }

    /**
     * Build the full PAYMENT-REQUIRED response payload.
     */
    public PaymentRequirement.PaymentRequiredResponse buildPaymentRequiredResponse(SubscriptionTier targetTier) {
        return PaymentRequirement.PaymentRequiredResponse.builder()
                .x402Version(1)
                .accepts(List.of(buildPaymentRequirement(targetTier)))
                .build();
    }

    /**
     * Verify a payment using the CDP Facilitator API.
     *
     * @param paymentPayload The base64-encoded payment payload from X-PAYMENT
     *                       header
     *                       (this is the JSON object the client sends, base64
     *                       encoded)
     * @param requirement    The payment requirement to verify against
     * @return True if payment is valid
     */
    public boolean verifyPayment(String paymentPayload, PaymentRequirement requirement) {
        try {
            log.debug("Received payment payload (first 100 chars): {}",
                    paymentPayload.length() > 100 ? paymentPayload.substring(0, 100) + "..." : paymentPayload);

            // Parse the payment payload - may be raw JSON or Base64-encoded JSON
            Map<String, Object> paymentPayloadMap = parsePaymentPayload(paymentPayload);

            log.debug("Parsed payment payload keys: {}", paymentPayloadMap.keySet());

            Map<String, Object> requestBody = Map.of(
                    "x402Version", 1,
                    "paymentPayload", paymentPayloadMap,
                    "paymentRequirements", Map.of(
                            "scheme", requirement.getScheme(),
                            "network", requirement.getNetwork(),
                            "maxAmountRequired", requirement.getPrice().replace("$", ""),
                            "resource", "/api/users/upgrade",
                            "description", requirement.getDescription(),
                            "mimeType", "application/json",
                            "outputSchema", Map.of(),
                            "payTo", requirement.getPayTo(),
                            "maxTimeoutSeconds", 60,
                            "asset", requirement.getAsset()));

            String jsonBody = objectMapper.writeValueAsString(requestBody);
            log.debug("CDP verify request body: {}", jsonBody);

            String jwt = generateJwt("POST", "/platform/v2/x402/verify");

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(cdpApiUrl + "/v2/x402/verify"))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + jwt)
                    .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode responseJson = objectMapper.readTree(response.body());
                boolean isValid = responseJson.path("isValid").asBoolean(false);
                log.debug("CDP verify response: valid={}, body={}", isValid, response.body());
                return isValid;
            } else {
                log.error("CDP verify API error: {} - {}", response.statusCode(), response.body());
                return false;
            }
        } catch (Exception e) {
            log.error("Failed to verify payment", e);
            return false;
        }
    }

    /**
     * Settle a payment using the CDP Facilitator API.
     *
     * @param paymentPayload The base64-encoded payment payload from X-PAYMENT
     *                       header
     * @param requirement    The payment requirement
     * @return Settlement response with transaction ID, or null if failed
     */
    public SettlementResult settlePayment(String paymentPayload, PaymentRequirement requirement) {
        try {
            // Parse the payment payload - may be raw JSON or Base64-encoded JSON
            Map<String, Object> paymentPayloadMap = parsePaymentPayload(paymentPayload);

            Map<String, Object> requestBody = Map.of(
                    "x402Version", 1,
                    "paymentPayload", paymentPayloadMap,
                    "paymentRequirements", Map.of(
                            "scheme", requirement.getScheme(),
                            "network", requirement.getNetwork(),
                            "maxAmountRequired", requirement.getPrice().replace("$", ""),
                            "resource", "/api/users/upgrade",
                            "description", requirement.getDescription(),
                            "mimeType", "application/json",
                            "outputSchema", Map.of(),
                            "payTo", requirement.getPayTo(),
                            "maxTimeoutSeconds", 60,
                            "asset", requirement.getAsset()));

            String jsonBody = objectMapper.writeValueAsString(requestBody);
            log.debug("CDP settle request body: {}", jsonBody);

            String jwt = generateJwt("POST", "/platform/v2/x402/settle");

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(cdpApiUrl + "/v2/x402/settle"))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + jwt)
                    .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode responseJson = objectMapper.readTree(response.body());
                log.debug("CDP settle response: {}", response.body());
                return new SettlementResult(
                        true,
                        responseJson.path("transactionHash").asText(null),
                        responseJson.path("networkId").asText(null));
            } else {
                log.error("CDP settle API error: {} - {}", response.statusCode(), response.body());
                return new SettlementResult(false, null, null);
            }
        } catch (Exception e) {
            log.error("Failed to settle payment", e);
            return new SettlementResult(false, null, null);
        }
    }

    /**
     * Parse the payment payload from the PAYMENT-SIGNATURE header.
     * The payload should be a Base64-encoded JSON object with structure:
     * {
     * "x402Version": 1,
     * "scheme": "exact",
     * "network": "eip155:84532",
     * "payload": { "signature": "0x...", "authorization": {...} }
     * }
     *
     * @param paymentPayload The raw payload from the header
     * @return Parsed Map of the payment payload
     */
    private Map<String, Object> parsePaymentPayload(String paymentPayload) throws Exception {
        String trimmed = paymentPayload.trim();

        // Check if payload is a raw hex signature (0x...) - this is incorrect format
        if (trimmed.startsWith("0x")) {
            log.error("PAYMENT-SIGNATURE header contains a raw hex signature. " +
                    "The x402 protocol requires a Base64-encoded JSON payload containing " +
                    "x402Version, scheme, network, and payload fields. " +
                    "Make sure the client is using an x402 SDK (@x402/fetch, @x402/axios, etc.) " +
                    "that properly wraps the signature.");
            throw new IllegalArgumentException(
                    "Invalid PAYMENT-SIGNATURE format: received raw hex signature (0x...). " +
                            "Expected Base64-encoded JSON payload from x402 client SDK.");
        }

        // Try to parse as raw JSON first
        if (trimmed.startsWith("{")) {
            try {
                log.debug("Attempting to parse as raw JSON");
                return objectMapper.readValue(trimmed,
                        new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {
                        });
            } catch (Exception e) {
                log.debug("Failed to parse as raw JSON: {}", e.getMessage());
            }
        }

        // Try Base64 decoding
        try {
            log.debug("Attempting to parse as Base64-encoded JSON");
            String decoded = new String(Base64.getDecoder().decode(trimmed), StandardCharsets.UTF_8);
            log.debug("Base64 decoded to: {}", decoded.length() > 100 ? decoded.substring(0, 100) + "..." : decoded);
            return objectMapper.readValue(decoded,
                    new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {
                    });
        } catch (Exception e) {
            log.debug("Failed to parse as Base64: {}", e.getMessage());
        }

        // Try URL-safe Base64 decoding
        try {
            log.debug("Attempting to parse as URL-safe Base64-encoded JSON");
            String decoded = new String(Base64.getUrlDecoder().decode(trimmed), StandardCharsets.UTF_8);
            return objectMapper.readValue(decoded,
                    new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {
                    });
        } catch (Exception e) {
            log.debug("Failed to parse as URL-safe Base64: {}", e.getMessage());
        }

        throw new IllegalArgumentException(
                "Could not parse PAYMENT-SIGNATURE as JSON or Base64-encoded JSON. " +
                        "Expected format: Base64-encoded JSON object with x402Version, scheme, network, and payload fields.");
    }

    /**
     * Generate a JWT for CDP API authentication.
     * Uses ES256 signing with the CDP API key.
     * 
     * @param method HTTP method (GET, POST, etc.)
     * @param path   API path (e.g., "/v2/x402/verify")
     */
    private String generateJwt(String method, String path) throws Exception {
        long now = Instant.now().getEpochSecond();
        String nonce = UUID.randomUUID().toString().replace("-", "");

        // Extract host from URL (e.g., "api.cdp.coinbase.com")
        String host = cdpApiUrl.replaceFirst("https?://", "").replaceFirst("/.*", "");
        // Build URI in format: "METHOD host/path" (e.g., "POST
        // api.cdp.coinbase.com/platform/v2/x402/verify")
        String uri = method + " " + host + path;

        log.debug("JWT uri claim: {}", uri);

        // JWT Header - per Coinbase docs
        Map<String, Object> header = Map.of(
                "alg", "ES256",
                "kid", cdpKeyName,
                "typ", "JWT",
                "nonce", nonce);

        // JWT Payload - per Coinbase docs (Python example)
        // Required claims: sub, iss, nbf, exp, uri
        Map<String, Object> payload = Map.of(
                "sub", cdpKeyName,
                "iss", "cdp",
                "nbf", now,
                "exp", now + 120, // 2 minute expiry
                "uri", uri);

        String headerBase64 = base64UrlEncode(objectMapper.writeValueAsBytes(header));
        String payloadBase64 = base64UrlEncode(objectMapper.writeValueAsBytes(payload));
        String signingInput = headerBase64 + "." + payloadBase64;

        // Sign with ES256
        String signature = signEs256(signingInput, cdpKeySecret);

        return signingInput + "." + signature;
    }

    private String signEs256(String data, String keyInput) throws Exception {
        // Clean the key input: remove PEM headers, escaped newlines, and whitespace
        // Note: Environment variables may contain literal "\n" as two characters
        // instead of actual newlines
        String cleanKey = keyInput
                .replace("-----BEGIN EC PRIVATE KEY-----", "")
                .replace("-----END EC PRIVATE KEY-----", "")
                .replace("-----BEGIN PRIVATE KEY-----", "")
                .replace("-----END PRIVATE KEY-----", "")
                .replace("\\n", "") // Handle escaped newlines from env vars
                .replaceAll("\\s+", "");

        log.debug("Cleaned key length: {} characters", cleanKey.length());
        byte[] keyBytes = Base64.getDecoder().decode(cleanKey);
        log.debug("Decoded key bytes length: {}", keyBytes.length);

        java.security.PrivateKey privateKey = null;
        KeyFactory keyFactory = KeyFactory.getInstance("EC");

        try {
            // 1. Try treating it as a standard PKCS8 key (-----BEGIN PRIVATE KEY-----)
            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(keyBytes);
            privateKey = keyFactory.generatePrivate(keySpec);
            log.debug("Successfully parsed key as PKCS8 format");
        } catch (Exception pkcs8Error) {
            log.debug("Failed to parse as PKCS8, trying SEC1 EC format: {}", pkcs8Error.getMessage());

            try {
                // 2. Try SEC1 EC private key format (-----BEGIN EC PRIVATE KEY-----)
                // This is what CDP provides. The 32-byte private scalar is at a fixed offset in
                // the ASN.1 structure.
                // SEC1 structure for P-256: SEQUENCE { version, privateKey (OCTET STRING), [0]
                // parameters, [1] publicKey }
                // The private key octet string (32 bytes for P-256) starts at byte offset 7 in
                // standard SEC1 encoding
                byte[] privateKeyBytes = extractSec1PrivateKey(keyBytes);
                log.debug("Extracted SEC1 private key scalar: {} bytes", privateKeyBytes.length);

                // Wrap in PKCS8 format for Java's KeyFactory
                privateKey = wrapRawKeyToPkcs8(keyFactory, privateKeyBytes);
                log.debug("Successfully parsed key as SEC1 EC format");
            } catch (Exception sec1Error) {
                log.debug("Failed to parse as SEC1, trying raw format: {}", sec1Error.getMessage());

                // 3. Final fallback: raw private key scalar (32 or 64 bytes)
                byte[] privateKeyBytes;
                if (keyBytes.length == 64) {
                    // Raw format: first 32 bytes are the private scalar
                    privateKeyBytes = new byte[32];
                    System.arraycopy(keyBytes, 0, privateKeyBytes, 0, 32);
                } else if (keyBytes.length == 32) {
                    privateKeyBytes = keyBytes;
                } else {
                    throw new IllegalArgumentException(
                            "Cannot parse EC private key. Length: " + keyBytes.length +
                                    " bytes. Expected PKCS8, SEC1, or raw 32/64 byte format.");
                }

                privateKey = wrapRawKeyToPkcs8(keyFactory, privateKeyBytes);
                log.debug("Successfully parsed key as raw format");
            }
        }

        Signature sig = Signature.getInstance("SHA256withECDSA");
        sig.initSign(privateKey);
        sig.update(data.getBytes(StandardCharsets.UTF_8));
        byte[] signatureBytes = sig.sign();

        // Convert from DER to P1363 format (fixed 64 bytes for ES256)
        byte[] p1363Signature = derToP1363(signatureBytes);
        return base64UrlEncode(p1363Signature);
    }

    /**
     * Extract the 32-byte private key scalar from a SEC1 EC private key structure.
     * SEC1 format (RFC 5915): SEQUENCE { version INTEGER, privateKey OCTET STRING,
     * ... }
     */
    private byte[] extractSec1PrivateKey(byte[] sec1Bytes) {
        // Parse the ASN.1 structure to find the OCTET STRING containing the private key
        // For P-256 keys, the structure is typically:
        // 30 77 (SEQUENCE, 119 bytes)
        // 02 01 01 (INTEGER, version = 1)
        // 04 20 <32 bytes> (OCTET STRING, private key)
        // ...optional tagged parameters and public key...

        int offset = 0;

        // Skip SEQUENCE tag and length
        if (sec1Bytes[offset] != 0x30) {
            throw new IllegalArgumentException("Invalid SEC1 format: expected SEQUENCE tag");
        }
        offset++;

        // Handle length byte(s)
        int seqLength = sec1Bytes[offset] & 0xff;
        offset++;
        if ((seqLength & 0x80) != 0) {
            // Long form length
            int numLengthBytes = seqLength & 0x7f;
            offset += numLengthBytes;
        }

        // Skip version INTEGER (02 01 01)
        if (sec1Bytes[offset] != 0x02) {
            throw new IllegalArgumentException("Invalid SEC1 format: expected INTEGER tag for version");
        }
        offset++;
        int versionLength = sec1Bytes[offset] & 0xff;
        offset++;
        offset += versionLength; // Skip version value

        // Now we should be at the OCTET STRING containing the private key
        if (sec1Bytes[offset] != 0x04) {
            throw new IllegalArgumentException("Invalid SEC1 format: expected OCTET STRING tag for private key");
        }
        offset++;
        int keyLength = sec1Bytes[offset] & 0xff;
        offset++;

        if (keyLength != 32) {
            throw new IllegalArgumentException("Invalid SEC1 format: expected 32-byte private key, got " + keyLength);
        }

        byte[] privateKey = new byte[32];
        System.arraycopy(sec1Bytes, offset, privateKey, 0, 32);
        return privateKey;
    }

    /**
     * Wrap a raw 32-byte EC private key scalar in PKCS8 format for Java KeyFactory.
     */
    private java.security.PrivateKey wrapRawKeyToPkcs8(KeyFactory keyFactory, byte[] privateKeyBytes)
            throws Exception {
        // PKCS8 header for P-256 EC private key
        byte[] pkcs8Header = new byte[] {
                0x30, (byte) 0x41, 0x02, 0x01, 0x00, 0x30, 0x13, 0x06, 0x07,
                0x2a, (byte) 0x86, 0x48, (byte) 0xce, 0x3d, 0x02, 0x01, 0x06, 0x08,
                0x2a, (byte) 0x86, 0x48, (byte) 0xce, 0x3d, 0x03, 0x01, 0x07, 0x04, 0x27,
                0x30, 0x25, 0x02, 0x01, 0x01, 0x04, 0x20
        };

        byte[] pkcs8Key = new byte[pkcs8Header.length + privateKeyBytes.length];
        System.arraycopy(pkcs8Header, 0, pkcs8Key, 0, pkcs8Header.length);
        System.arraycopy(privateKeyBytes, 0, pkcs8Key, pkcs8Header.length, privateKeyBytes.length);

        PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(pkcs8Key);
        return keyFactory.generatePrivate(keySpec);
    }

    private byte[] derToP1363(byte[] derSignature) {
        // Simple DER to P1363 conversion for ES256 (32+32 = 64 bytes)
        int offset = 3;
        int rLength = derSignature[offset++] & 0xff;
        byte[] r = new byte[32];
        if (rLength > 32) {
            System.arraycopy(derSignature, offset + (rLength - 32), r, 0, 32);
        } else {
            System.arraycopy(derSignature, offset, r, 32 - rLength, rLength);
        }
        offset += rLength + 1;

        int sLength = derSignature[offset++] & 0xff;
        byte[] s = new byte[32];
        if (sLength > 32) {
            System.arraycopy(derSignature, offset + (sLength - 32), s, 0, 32);
        } else {
            System.arraycopy(derSignature, offset, s, 32 - sLength, sLength);
        }

        byte[] result = new byte[64];
        System.arraycopy(r, 0, result, 0, 32);
        System.arraycopy(s, 0, result, 32, 32);
        return result;
    }

    private String base64UrlEncode(byte[] data) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(data);
    }

    /**
     * Result of a payment settlement operation.
     */
    public record SettlementResult(boolean success, String transactionHash, String networkId) {
    }
}
