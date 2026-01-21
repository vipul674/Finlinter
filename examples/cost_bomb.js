/**
 * JavaScript Cost Bomb Example
 * 
 * This file demonstrates patterns that FinLinter should detect.
 * These are common anti-patterns that cause excessive cloud costs.
 */

const axios = require('axios');

// Simulated database connection
const db = {
    collection: (name) => ({
        find: (query) => Promise.resolve([]),
        findOne: (query) => Promise.resolve({}),
    })
};

/**
 * BAD: Multiple API calls inside a loop.
 */
async function processOrders(orderIds) {
    const results = [];

    for (const orderId of orderIds) {
        // BAD: fetch() call in loop
        const response = await fetch(`https://api.example.com/orders/${orderId}`);
        const data = await response.json();

        // BAD: axios call in loop
        const enrichment = await axios.get(`https://api.example.com/enrichment/${orderId}`);

        // BAD: JSON.stringify in loop
        const serialized = JSON.stringify(data);

        results.push({ data, enrichment: enrichment.data, serialized });
    }

    return results;
}


/**
 * BAD: Database calls in forEach loop.
 */
async function enrichUsers(users) {
    const enriched = [];

    users.forEach(async (user) => {
        // BAD: MongoDB find inside forEach
        const profile = await db.collection('profiles').findOne({ userId: user.id });

        // BAD: API call inside forEach
        const external = await fetch(`https://api.external.com/user/${user.id}`);

        enriched.push({ ...user, profile });
    });

    return enriched;
}


/**
 * BAD: Promise creation inside loop causes unbounded fan-out.
 */
function fanOutRequests(items) {
    const promises = [];

    for (let i = 0; i < items.length; i++) {
        // BAD: Promise created in loop - unbounded concurrency
        const promise = new Promise((resolve) => {
            fetch(`https://api.example.com/items/${items[i]}`)
                .then(r => r.json())
                .then(resolve);
        });
        promises.push(promise);
    }

    return Promise.all(promises);
}


/**
 * BAD: Database aggregation in loop.
 */
async function handleRequest(req) {
    const categories = req.body.categories;

    for (const category of categories) {
        // BAD: MongoDB aggregate in loop
        const stats = await db.collection('products').aggregate([
            { $match: { category } },
            { $group: { _id: null, total: { $sum: 1 } } }
        ]);

        // BAD: JSON.parse in loop
        const parsed = JSON.parse(req.body.data);
    }
}


/**
 * BAD: Array method with API calls.
 */
async function mapWithFetch(ids) {
    // BAD: fetch inside map (even with Promise.all, each creates a request)
    const results = await Promise.all(
        ids.map(async (id) => {
            const res = await fetch(`https://api.example.com/${id}`);
            return res.json();
        })
    );

    return results;
}


// ============================================================
// GOOD PATTERNS (for comparison - should NOT trigger warnings)
// ============================================================

/**
 * GOOD: Single batch API call.
 */
async function processOrdersCorrectly(orderIds) {
    // GOOD: Single batch request
    const response = await fetch('https://api.example.com/orders/batch', {
        method: 'POST',
        body: JSON.stringify({ ids: orderIds }),
    });

    const allData = await response.json();

    // Processing without I/O is fine
    const results = orderIds.map(id => ({
        id,
        data: allData[id]
    }));

    // GOOD: Single serialization at the end
    return JSON.stringify(results);
}
