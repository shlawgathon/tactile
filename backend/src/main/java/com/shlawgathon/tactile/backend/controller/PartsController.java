package com.shlawgathon.tactile.backend.controller;

import com.shlawgathon.tactile.backend.dto.PaymentRequirement;
import com.shlawgathon.tactile.backend.service.X402Service;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Controller for x402-protected parts catalog.
 * Demonstrates end-to-end x402 payment flow with test USDC on Base Sepolia.
 */
@RestController
@RequestMapping("/api/parts")
@Tag(name = "Parts", description = "x402-protected parts catalog for agent purchases")
public class PartsController {

    private static final Logger log = LoggerFactory.getLogger(PartsController.class);

    private final X402Service x402Service;

    @Value("${cdp.x402.network}")
    private String network;

    @Value("${cdp.x402.asset}")
    private String asset;

    @Value("${cdp.x402.pay-to-address}")
    private String payToAddress;

    // Parts catalog with prices in USD
    private static final List<Map<String, Object>> PARTS_CATALOG = List.of(
            Map.of(
                    "partNumber", "MC-M3X10-SHCS",
                    "name", "M3 x 10mm Socket Head Cap Screw",
                    "category", "fasteners",
                    "manufacturer", "McMaster-Carr",
                    "priceUsd", 0.01,
                    "cadUrl", "/api/parts/MC-M3X10-SHCS/cad"),
            Map.of(
                    "partNumber", "MC-MR63ZZ",
                    "name", "MR63ZZ Miniature Ball Bearing (3x6x2.5mm)",
                    "category", "bearings",
                    "manufacturer", "McMaster-Carr",
                    "priceUsd", 0.02,
                    "cadUrl", "/api/parts/MC-MR63ZZ/cad"),
            Map.of(
                    "partNumber", "NEMA17-42",
                    "name", "NEMA 17 Stepper Motor (42x42mm)",
                    "category", "motors",
                    "manufacturer", "StepperOnline",
                    "priceUsd", 0.05,
                    "cadUrl", "/api/parts/NEMA17-42/cad"),
            Map.of(
                    "partNumber", "LM8UU",
                    "name", "LM8UU Linear Ball Bearing (8mm)",
                    "category", "linear_motion",
                    "manufacturer", "Generic",
                    "priceUsd", 0.01,
                    "cadUrl", "/api/parts/LM8UU/cad"));

    public PartsController(X402Service x402Service) {
        this.x402Service = x402Service;
    }

    /**
     * Search parts catalog (free endpoint).
     */
    @GetMapping("/search")
    @Operation(summary = "Search parts", description = "Search the parts catalog by query (free)")
    public ResponseEntity<Map<String, Object>> searchParts(
            @RequestParam(required = false) String query,
            @RequestParam(required = false) String category) {

        List<Map<String, Object>> results = PARTS_CATALOG.stream()
                .filter(part -> {
                    if (query != null && !query.isBlank()) {
                        String q = query.toLowerCase();
                        String name = ((String) part.get("name")).toLowerCase();
                        String partNum = ((String) part.get("partNumber")).toLowerCase();
                        if (!name.contains(q) && !partNum.contains(q)) {
                            return false;
                        }
                    }
                    if (category != null && !category.isBlank()) {
                        String cat = (String) part.get("category");
                        if (!cat.equalsIgnoreCase(category)) {
                            return false;
                        }
                    }
                    return true;
                })
                .toList();

        return ResponseEntity.ok(Map.of(
                "success", true,
                "count", results.size(),
                "results", results));
    }

    /**
     * Get part CAD data - requires x402 payment.
     */
    @GetMapping("/{partNumber}/cad")
    @Operation(summary = "Get part CAD", description = "Download CAD data for a part (requires x402 payment)")
    public ResponseEntity<Object> getPartCad(
            @PathVariable String partNumber,
            @RequestHeader(value = "X-PAYMENT", required = false) String paymentHeader) {

        // Find the part
        Map<String, Object> part = PARTS_CATALOG.stream()
                .filter(p -> partNumber.equals(p.get("partNumber")))
                .findFirst()
                .orElse(null);

        if (part == null) {
            return ResponseEntity.notFound().build();
        }

        double priceUsd = (double) part.get("priceUsd");
        long amountInSmallestUnit = (long) (priceUsd * 1_000_000); // USDC has 6 decimals

        // Build payment requirement
        PaymentRequirement requirement = PaymentRequirement.builder()
                .scheme("exact")
                .network(network)
                .price("$" + String.format("%.2f", priceUsd))
                .maxAmountRequired(String.valueOf(amountInSmallestUnit))
                .payTo(payToAddress)
                .asset(asset)
                .description("CAD download for " + part.get("name"))
                .name("USD Coin")
                .version("2")
                .extra(PaymentRequirement.Extra.builder()
                        .name("USD Coin")
                        .version("2")
                        .build())
                .build();

        // If no payment header, return 402 Payment Required
        if (paymentHeader == null || paymentHeader.isBlank()) {
            log.info("No payment header for CAD request: {}", partNumber);

            PaymentRequirement.PaymentRequiredResponse response = PaymentRequirement.PaymentRequiredResponse.builder()
                    .x402Version(1)
                    .paymentRequirements(List.of(requirement))
                    .build();

            return ResponseEntity.status(HttpStatus.PAYMENT_REQUIRED)
                    .header("X-PAYMENT-RESPONSE", "payment_required")
                    .body(response);
        }

        // Verify the payment
        log.info("Verifying payment for CAD: {}", partNumber);
        boolean isValid = x402Service.verifyPayment(paymentHeader, requirement);

        if (!isValid) {
            log.warn("Payment verification failed for: {}", partNumber);
            return ResponseEntity.status(HttpStatus.PAYMENT_REQUIRED)
                    .body(Map.of("error", "Payment verification failed"));
        }

        // Settle the payment
        log.info("Settling payment for CAD: {}", partNumber);
        X402Service.SettlementResult settlement = x402Service.settlePayment(paymentHeader, requirement);

        if (settlement == null || !settlement.success()) {
            log.error("Payment settlement failed for: {}", partNumber);
            return ResponseEntity.status(HttpStatus.PAYMENT_REQUIRED)
                    .body(Map.of("error", "Payment settlement failed"));
        }

        log.info("Payment successful for CAD: {}, txHash: {}",
                partNumber, settlement.transactionHash());

        // Return mock CAD data (in real implementation, return actual STEP file)
        String mockCadData = String.format("""
                # STEP file for %s
                # Part Number: %s
                # Generated for x402 payment demo
                # Transaction: %s

                ISO-10303-21;
                HEADER;
                FILE_DESCRIPTION(('Demo CAD File'),'2;1');
                FILE_NAME('%s.step','2024-01-01T00:00:00',('tactile3d'),(''),'',' ','');
                FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
                ENDSEC;
                DATA;
                #1=SHAPE_REPRESENTATION('demo',(#2),#3);
                #2=AXIS2_PLACEMENT_3D('',#4,#5,#6);
                #3=( GEOMETRIC_REPRESENTATION_CONTEXT(3)
                    GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#7))
                    GLOBAL_UNIT_ASSIGNED_CONTEXT((#8,#9,#10))
                    REPRESENTATION_CONTEXT('Context','') );
                ENDSEC;
                END-ISO-10303-21;
                """, part.get("name"), partNumber, settlement.transactionHash(), partNumber);

        return ResponseEntity.ok()
                .header("X-PAYMENT-RESPONSE", settlement.transactionHash())
                .header("Content-Type", "application/step")
                .body(Map.of(
                        "success", true,
                        "partNumber", partNumber,
                        "transactionHash", settlement.transactionHash(),
                        "cadData", mockCadData));
    }

    /**
     * Get individual part details (free).
     */
    @GetMapping("/{partNumber}")
    @Operation(summary = "Get part details", description = "Get part metadata (free)")
    public ResponseEntity<Object> getPartDetails(@PathVariable String partNumber) {
        Map<String, Object> part = PARTS_CATALOG.stream()
                .filter(p -> partNumber.equals(p.get("partNumber")))
                .findFirst()
                .orElse(null);

        if (part == null) {
            return ResponseEntity.notFound().build();
        }

        return ResponseEntity.ok(part);
    }
}
