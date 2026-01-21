package com.example.costbomb;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.List;
import java.util.ArrayList;

/**
 * Java Cost Bomb Example
 * 
 * This class demonstrates patterns that FinLinter should detect.
 * These are common anti-patterns that cause excessive cloud costs.
 */
@Service
public class CostBomb {

    @Autowired
    private UserRepository repository;
    
    @Autowired
    private RestTemplate restTemplate;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Autowired
    private JdbcTemplate jdbcTemplate;

    /**
     * BAD: Multiple repository and API calls inside a loop.
     */
    public List<UserDTO> processUsers(List<Long> userIds) {
        List<UserDTO> results = new ArrayList<>();
        
        for (Long userId : userIds) {
            // BAD: Spring Data repository call in loop
            User user = repository.findById(userId).orElse(null);
            
            // BAD: RestTemplate call in loop
            EnrichmentData enrichment = restTemplate.getForObject(
                "https://api.example.com/enrichment/" + userId,
                EnrichmentData.class
            );
            
            // BAD: ObjectMapper serialization in loop
            try {
                String serialized = objectMapper.writeValueAsString(user);
            } catch (Exception e) {
                // Handle exception
            }
            
            results.add(new UserDTO(user, enrichment));
        }
        
        return results;
    }

    /**
     * BAD: JDBC queries inside a loop.
     */
    public void processOrders(List<String> orderIds) {
        for (String orderId : orderIds) {
            // BAD: JdbcTemplate query in loop
            Order order = jdbcTemplate.queryForObject(
                "SELECT * FROM orders WHERE id = ?",
                new Object[]{orderId},
                Order.class
            );
            
            // BAD: Another JDBC query in same loop
            List<OrderItem> items = jdbcTemplate.query(
                "SELECT * FROM order_items WHERE order_id = ?",
                new Object[]{orderId},
                new OrderItemMapper()
            );
        }
    }

    /**
     * BAD: HTTP calls in a stream operation.
     */
    public void processWithStream(List<Long> ids) {
        ids.stream()
            .forEach(id -> {
                // BAD: RestTemplate inside forEach (stream)
                Object result = restTemplate.exchange(
                    "https://api.example.com/data/" + id,
                    HttpMethod.GET,
                    null,
                    Object.class
                );
            });
    }

    /**
     * BAD: Entity Manager queries in loop (JPA).
     */
    public void handleRequest(List<String> keys) {
        for (String key : keys) {
            // BAD: EntityManager find in loop
            Entity entity = entityManager.find(Entity.class, key);
            
            // BAD: EntityManager query in loop
            Query query = entityManager.createQuery(
                "SELECT e FROM Entity e WHERE e.key = :key"
            );
        }
    }

    /**
     * BAD: DynamoDB calls in loop (AWS SDK).
     */
    public void processDynamoDB(List<String> ids) {
        for (String id : ids) {
            // BAD: DynamoDB getItem in loop
            GetItemResult result = dynamoDb.getItem(
                new GetItemRequest()
                    .withTableName("products")
                    .withKey(Collections.singletonMap("id", new AttributeValue(id)))
            );
        }
    }

    // ============================================================
    // GOOD PATTERNS (for comparison - should NOT trigger warnings)
    // ============================================================

    /**
     * GOOD: Batch operations.
     */
    public List<UserDTO> processUsersCorrectly(List<Long> userIds) {
        // GOOD: Single batch call
        List<User> users = repository.findAllById(userIds);
        
        // GOOD: Single API call for batch
        BatchEnrichmentResponse enrichment = restTemplate.postForObject(
            "https://api.example.com/batch-enrichment",
            new BatchRequest(userIds),
            BatchEnrichmentResponse.class
        );
        
        List<UserDTO> results = new ArrayList<>();
        for (User user : users) {
            // Processing without I/O is fine
            results.add(new UserDTO(user, enrichment.get(user.getId())));
        }
        
        // GOOD: Single serialization at the end
        return results;
    }
}

// Placeholder classes for compilation
class User {}
class UserDTO {
    UserDTO(User user, Object enrichment) {}
}
class EnrichmentData {}
class Order {}
class OrderItem {}
class OrderItemMapper {}
class Entity {}
class Query {}
class GetItemResult {}
class GetItemRequest {
    GetItemRequest withTableName(String name) { return this; }
    GetItemRequest withKey(Object key) { return this; }
}
class AttributeValue {
    AttributeValue(String value) {}
}
class BatchRequest {
    BatchRequest(List<Long> ids) {}
}
class BatchEnrichmentResponse {
    Object get(Object id) { return null; }
}
interface UserRepository {
    java.util.Optional<User> findById(Long id);
    List<User> findAllById(Iterable<Long> ids);
}
