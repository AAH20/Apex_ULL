# Ultra-Low-Latency Data Structures

Design patterns and analysis for data structures optimized for sub-microsecond latency, high throughput, and cache-friendly memory access.

---

## Table of Contents

1. [Ring Buffer (SPSC / MPMC)](#1-ring-buffer)
2. [Circular Array](#2-circular-array)
3. [Hash Map (Open Addressing)](#3-hash-map)
4. [Skip List](#4-skip-list)
5. [B-Tree](#5-b-tree)
6. [Radix Tree (ART)](#6-radix-tree)
7. [Custom Structures](#7-custom-structures)
8. [Selection Guide](#8-selection-guide)

---

## 1. Ring Buffer

### Overview

A fixed-size, contiguous memory buffer with head/tail indices that wrap around. The canonical ULL queue primitive.

### Variants

| Variant | Producers | Contenders | Use Case |
|---------|-----------|------------|----------|
| SPSC | 1 | 1 | LMAX Disruptor, kernel pipes |
| MPSC | N | 1 | Task queues, logging |
| SPMC | 1 | N | Work distribution |
| MPMC | N | N | General inter-thread |

### Design

```
┌──────────────────────────────────────────────┐
│  [0] [1] [2] [3] [4] [5] [6] [7] ... [N-1]  │
│       ↑ head              ↑ tail              │
│       (consumer)          (producer)          │
└──────────────────────────────────────────────┘
```

**SPSC Implementation (lock-free):**

```c
#define RING_SIZE 4096  // power of 2
#define RING_MASK (RING_SIZE - 1)

typedef struct {
    _Atomic uint64_t head;  // written by consumer
    _Atomic uint64_t tail;  // written by producer
    void *slots[RING_SIZE];
} spsc_ring_t;

// Producer: enqueue
bool spsc_push(spsc_ring_t *r, void *item) {
    uint64_t t = atomic_load_explicit(&r->tail, memory_order_relaxed);
    uint64_t h = atomic_load_explicit(&r->head, memory_order_acquire);
    if ((t - h) >= RING_SIZE) return false;  // full
    r->slots[t & RING_MASK] = item;
    atomic_store_explicit(&r->tail, t + 1, memory_order_release);
    return true;
}

// Consumer: dequeue
void *spsc_pop(spsc_ring_t *r) {
    uint64_t h = atomic_load_explicit(&r->head, memory_order_relaxed);
    uint64_t t = atomic_load_explicit(&r->tail, memory_order_acquire);
    if (h == t) return NULL;  // empty
    void *item = r->slots[h & RING_MASK];
    atomic_store_explicit(&r->head, h + 1, memory_order_release);
    return item;
}
```

**MPMC Implementation (Dmitry Vyukov's bounded queue):**

```c
typedef struct {
    _Atomic uint64_t sequence;
    void *slot;
} cell_t;

typedef struct {
    uint64_t mask;
    cell_t *cells;
    _Atomic uint64_t head;
    _Atomic uint64_t tail;
    char _pad[64];  // cache line padding
} mpmc_ring_t;

bool mpmc_push(mpmc_ring_t *r, void *item) {
    cell_t *cell;
    uint64_t pos = atomic_load_explicit(&r->head, memory_order_relaxed);
    for (;;) {
        cell = &r->cells[pos & r->mask];
        uint64_t seq = atomic_load_explicit(&cell->sequence, memory_order_acquire);
        int64_t diff = (int64_t)seq - (int64_t)pos;
        if (diff == 0) {
            if (atomic_compare_exchange_weak_explicit(
                    &r->head, &pos, pos + 1, memory_order_relaxed,
                    memory_order_relaxed))
                break;
        } else if (diff < 0) {
            return false;  // full
        } else {
            pos = atomic_load_explicit(&r->head, memory_order_relaxed);
        }
    }
    cell->slot = item;
    atomic_store_explicit(&cell->sequence, pos + 1, memory_order_release);
    return true;
}
```

### Performance Characteristics

| Metric | SPSC | MPMC (Vyukov) |
|--------|------|----------------|
| **Enqueue latency** | ~5 ns | ~25–50 ns |
| **Dequeue latency** | ~5 ns | ~25–50 ns |
| **Throughput** | ~200M ops/s/core | ~20–40M ops/s/core |
| **Memory footprint** | 8·N bytes (pointers) | 16·N bytes (seq + ptr) |
| **Cache lines touched** | 1 (producer) + 1 (consumer) | 2–4 (CAS contention) |
| **Ordering guarantee** | Sequential consistency | Per-cell sequential consistency |

### Cache Efficiency

- **SPSC**: Producer and consumer touch different cache lines (head vs. tail). Zero false sharing with padding. Each operation touches exactly 1 cache line for the index + 1 for the slot.
- **MPMC**: CAS on shared `head`/`tail` causes cache line bouncing. Vyukov's per-cell sequence numbers reduce contention but still require acquire/release on each cell.
- **Power-of-2 sizing**: Enables bitmask (`& mask`) instead of modulo (`% size`), saving ~20 cycles per index calculation.

### When to Use

- Inter-thread communication (SPSC for 1:1, MPSC for N:1)
- Kernel-bypass networking (DPDK, Solarflare Onload)
- LMAX Disruptor pattern for event processing
- Audio/video streaming pipelines

---

## 2. Circular Array

### Overview

A dynamic array that reuses slots via modular indexing. Unlike a ring buffer, it supports random access and is typically single-threaded or externally synchronized.

### Design

```c
typedef struct {
    void **slots;
    uint32_t head;   // oldest element
    uint32_t count;  // number of elements
    uint32_t cap;    // capacity (power of 2)
} circ_array_t;

// O(1) push back
void circ_push_back(circ_array_t *a, void *item) {
    uint32_t tail = (a->head + a->count) & (a->cap - 1);
    a->slots[tail] = item;
    if (a->count < a->cap) a->count++;
    else a->head = (a->head + 1) & (a->cap - 1);  // overwrite oldest
}

// O(1) random access
void *circ_get(circ_array_t *a, uint32_t idx) {
    return a->slots[(a->head + idx) & (a->cap - 1)];
}

// O(1) pop front
void *circ_pop_front(circ_array_t *a) {
    if (a->count == 0) return NULL;
    void *item = a->slots[a->head];
    a->head = (a->head + 1) & (a->cap - 1);
    a->count--;
    return item;
}
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Push back** | ~3 ns |
| **Random access** | ~2 ns |
| **Pop front** | ~3 ns |
| **Memory footprint** | 8·N bytes + 16 bytes header |
| **Cache lines touched** | 1 (sequential scan: N/8 lines) |
| **Resize cost** | O(n) copy (amortized O(1)) |

### Cache Efficiency

- **Sequential scan**: Perfect prefetching. Hardware prefetcher detects stride-1 access pattern.
- **Random access**: 1 cache line per access (8-byte pointers, 8 per line on 64-byte lines).
- **Overwrite mode**: No allocation, no GC pressure. Ideal for sliding windows.

### When to Use

- Sliding window statistics (moving average, VWAP)
- Time-series buffers with overwrite
- Single-threaded LRU approximation
- Order book price level caching

---

## 3. Hash Map

### Overview

Open-addressing hash map optimized for cache locality. Three variants: linear probing, Robin Hood hashing, and SwissTable (SIMD probing).

### Variant A: Linear Probing

```c
#define HT_SIZE (1 << 20)  // 1M entries
#define HT_MASK (HT_SIZE - 1)

typedef struct {
    uint64_t key;
    uint64_t value;
    uint8_t  hash;  // cached 8-bit hash
    uint8_t  state; // 0=empty, 1=occupied, 2=deleted
} ht_entry_t;

typedef struct {
    ht_entry_t *entries;
    uint32_t count;
    uint32_t mask;
} ht_map_t;

// Core lookup: ~1 cache line on hit
uint64_t ht_get(ht_map_t *m, uint64_t key) {
    uint8_t h = (uint8_t)(key * 0x9E3779B97F4A7C15ULL >> 56);
    uint32_t idx = h & m->mask;
    while (m->entries[idx].state != 0) {
        if (m->entries[idx].state == 1 && m->entries[idx].key == key)
            return m->entries[idx].value;
        idx = (idx + 1) & m->mask;
    }
    return 0;  // not found
}
```

### Variant B: Robin Hood Hashing

```c
// Entries track their "distance from ideal" (DFI)
// On insert: steal from the rich (low DFI), give to the poor (high DFI)
// Result: bounded probe length, ~2x variance reduction vs. linear probing

typedef struct {
    uint64_t key;
    uint64_t value;
    uint8_t  hash;
    int16_t  dfi;  // distance from ideal position
} rh_entry_t;

// Worst-case probe: ~10 at 95% load (vs. ~50+ for linear probing)
// Average probe: ~1.5 at 90% load
```

### Variant C: SwissTable (Google Abseil / Rust hashbrown)

```c
// Group = 16 bytes = 16 hash-byte slots
// SIMD: _mm_cmpeq_epi8 searches 16 slots in 1 instruction
// Control bytes: 0x80=empty, 0xFF=deleted, 0x00-0x7F=hash byte

typedef struct {
    uint8_t ctrl[16];   // 16 control bytes
    void *slots[16];    // 16 key-value pointers
} st_group_t;

// Lookup: 1 SIMD compare per group
// At 87.5% load: average ~1.1 groups probed = ~1.1 cache lines
__m128i target = _mm_set1_epi8((char)hash_byte);
__m128i match = _mm_cmpeq_epi8(target, _mm_loadu_si128((__m128i*)group->ctrl));
int mask = _mm_movemask_epi8(match);
```

### Performance Comparison

| Metric | Linear Probe | Robin Hood | SwissTable |
|--------|-------------|------------|------------|
| **Hit latency** | ~5 ns | ~5 ns | ~4 ns |
| **Miss latency** | ~15 ns | ~8 ns | ~6 ns |
| **Insert latency** | ~10 ns | ~15 ns | ~12 ns |
| **Delete** | Tombstone | Backshift | Tombstone |
| **Max load factor** | 0.7 | 0.9 | 0.875 |
| **Memory/entry** | 17 bytes | 18 bytes | 17 bytes |
| **Cache lines (hit)** | 1 | 1 | 1 |
| **Cache lines (miss)** | 2–5 | 1–2 | 1–2 |
| **SIMD friendly** | No | No | Yes (SSE2/NEON) |

### Memory Layout Optimization

```
SwissTable memory layout:
┌─────────────────────────────────────────┐
│  ctrl[0] ctrl[1] ... ctrl[15] │ pad     │  ← 17 bytes per group
├─────────────────────────────────────────┤
│  slot[0] slot[1] ... slot[15] │         │  ← 128 bytes per group
└─────────────────────────────────────────┘
Total: 145 bytes per 16 entries = ~9 bytes/entry
```

### When to Use

- **Linear probing**: Simple, good for small maps (< 1K entries)
- **Robin Hood**: Predictable worst-case, good for real-time systems
- **SwissTable**: Best overall, production default (Abseil, Rust std)

---

## 4. Skip List

### Overview

A probabilistic balanced structure providing O(log n) search/insert/delete with simpler implementation than balanced trees. Used in Redis (sorted sets), LevelDB (memtable), and in-memory databases.

### Design

```c
#define MAX_LEVEL 32
#define P 0.25  // probability of promoting to next level

typedef struct skip_node {
    uint64_t key;
    void *value;
    struct skip_node *forward[];  // flexible array: forward[0..level-1]
} skip_node_t;

typedef struct {
    skip_node_t *head;  // sentinel with MAX_LEVEL forward pointers
    uint32_t level;     // current max level
    uint32_t count;
} skip_list_t;

// Search: O(log n) expected
skip_node_t *skip_search(skip_list_t *sl, uint64_t key) {
    skip_node_t *x = sl->head;
    for (int i = sl->level - 1; i >= 0; i--) {
        while (x->forward[i] && x->forward[i]->key < key)
            x = x->forward[i];
    }
    x = x->forward[0];
    return (x && x->key == key) ? x : NULL;
}

// Insert: O(log n) expected
void skip_insert(skip_list_t *sl, uint64_t key, void *value) {
    skip_node_t *update[MAX_LEVEL];
    skip_node_t *x = sl->head;
    for (int i = sl->level - 1; i >= 0; i--) {
        while (x->forward[i] && x->forward[i]->key < key)
            x = x->forward[i];
        update[i] = x;
    }
    uint32_t lvl = random_level();  // geometric distribution
    if (lvl > sl->level) {
        for (uint32_t i = sl->level; i < lvl; i++)
            update[i] = sl->head;
        sl->level = lvl;
    }
    x = skip_node_alloc(lvl);
    x->key = key;
    x->value = value;
    for (uint32_t i = 0; i < lvl; i++) {
        x->forward[i] = update[i]->forward[i];
        update[i]->forward[i] = x;
    }
    sl->count++;
}
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Search** | ~50–200 ns (cache-dependent) |
| **Insert** | ~100–300 ns |
| **Delete** | ~100–300 ns |
| **Memory/entry** | ~24 + 8·E[level] bytes ≈ 32 bytes |
| **Cache lines per search** | log_{1/P}(n) ≈ 20 for 1M entries |
| **Expected levels** | log₂(n) + O(1) |

### Cache Efficiency Analysis

- **Poor locality**: Each forward pointer chase is a random access. ~20 cache misses for 1M entries.
- **Mitigation**: Use **unrolled skip lists** (each node holds multiple keys per level) to reduce pointer chases.
- **Alternative**: **B-skip lists** — B-tree-like blocking of skip list nodes.

### When to Use

- Concurrent ordered maps (lock-free variants exist)
- Range queries with O(log n) seek + O(k) iteration
- When simplicity > raw performance (Redis, LevelDB)
- As a building block for lock-free priority queues

---

## 5. B-Tree

### Overview

A self-balancing tree with high branching factor, minimizing cache misses. Each node fits in one or a few cache lines. The standard for disk-based and large in-memory indexes.

### Design (In-Memory B-Tree)

```c
#define BTREE_ORDER 16  // keys per node (tunable: 8–64)

typedef struct {
    uint64_t keys[BTREE_ORDER - 1];
    void *values[BTREE_ORDER - 1];
    struct bt_node *children[BTREE_ORDER];
    uint16_t num_keys;
    bool is_leaf;
} bt_node_t;

typedef struct {
    bt_node_t *root;
    uint32_t count;
} btree_t;

// Search: O(log_B n) where B = branching factor
// For 1M entries, B=16: depth = log_16(1M) ≈ 5
void *btree_search(btree_t *t, uint64_t key) {
    bt_node_t *node = t->root;
    while (node) {
        int i = 0;
        while (i < node->num_keys && key > node->keys[i]) i++;
        if (i < node->num_keys && key == node->keys[i])
            return node->values[i];
        node = node->is_leaf ? NULL : node->children[i];
    }
    return NULL;
}
```

### Performance Characteristics

| Metric | B=8 | B=16 | B=32 | B=64 |
|--------|-----|------|------|------|
| **Search latency** | ~80 ns | ~60 ns | ~50 ns | ~45 ns |
| **Insert latency** | ~150 ns | ~120 ns | ~100 ns | ~90 ns |
| **Depth (1M entries)** | 7 | 5 | 4 | 3 |
| **Cache lines/search** | 7 | 5 | 4 | 3 |
| **Memory/entry** | ~48 bytes | ~32 bytes | ~24 bytes | ~20 bytes |
| **Node size** | ~384 B | ~768 B | ~1536 B | ~3072 B |

### Cache Efficiency

- **Node size = cache line multiple**: B=16 with 8-byte keys/values → 16·8 + 16·8 + 17·8 + 2 ≈ 274 bytes ≈ 4–5 cache lines.
- **Binary search within node**: For B=16, 4 comparisons (log₂16) within a single cache line.
- **Prefetching**: Children can be prefetched during descent.
- **B+ tree variant**: All data in leaves, linked for range scans. Internal nodes are pure routing (higher effective branching).

### B+ Tree for Range Queries

```
Internal node:  [k1 | k2 | k3 | ... | k15]  (routing only)
                    ↓    ↓    ↓
Leaf nodes:    [k,v|k,v|...] ↔ [k,v|k,v|...] ↔ [k,v|k,v|...]
                ↑ linked list for O(k) range scan
```

### When to Use

- Database indexes (SQLite, PostgreSQL, MySQL InnoDB)
- Filesystems (NTFS, ext4, Btrfs)
- Large in-memory ordered maps (> 100K entries)
- Range queries with high selectivity

---

## 6. Radix Tree (ART — Adaptive Radix Tree)

### Overview

A space-optimized trie with adaptive node sizing. Compresses single-child paths and chooses node representation based on child count. Used in PostgreSQL, HyPer, and in-memory databases.

### Node Types (Adaptive)

```c
typedef enum { NODE4, NODE16, NODE48, NODE256 } art_node_type_t;

// NODE4: 1–4 children, linear search
typedef struct {
    art_node_type_t type;
    uint8_t num_children;
    uint8_t keys[4];
    void *children[4];
} art_node4_t;  // 4·1 + 4·8 + 3 = ~40 bytes

// NODE16: 5–16 children, SIMD search
typedef struct {
    art_node_type_t type;
    uint8_t num_children;
    uint8_t keys[16];
    void *children[16];
} art_node16_t;  // 16·1 + 16·8 + 2 = ~146 bytes

// NODE48: 17–48 children, 256-entry index
typedef struct {
    art_node_type_t type;
    uint8_t num_children;
    uint8_t child_index[256];  // 0 = empty, 1–48 = child index
    void *children[48];
} art_node48_t;  // 256 + 48·8 + 2 = ~642 bytes

// NODE256: 49–256 children, direct array
typedef struct {
    art_node_type_t type;
    uint8_t num_children;
    void *children[256];
} art_node256_t;  // 256·8 + 2 = ~2050 bytes
```

### Path Compression

```
Standard trie:  root → 'a' → 'p' → 'p' → 'l' → 'e' → value
                                    (5 nodes, 5 cache misses)

ART compressed: root → "apple" → value
                (1 node, 1 cache miss)

Internal nodes store partial keys (prefix) to skip redundant levels.
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Search** | ~20–50 ns (key-length dependent) |
| **Insert** | ~50–100 ns |
| **Delete** | ~50–100 ns |
| **Memory/entry** | ~10–30 bytes (with compression) |
| **Cache lines/search** | 1–3 (vs. 20+ for skip list) |
| **Key length sensitivity** | O(k) where k = key length |

### Cache Efficiency

- **Path compression**: Reduces tree depth from O(key_length) to O(distinct_prefixes).
- **Adaptive nodes**: Small nodes (NODE4) fit in 1 cache line. Large nodes (NODE256) amortize across many children.
- **SIMD on NODE16**: `_mm_cmpeq_epi8` finds matching child in 1 instruction.
- **Lazy expansion**: NODE4 → NODE16 → NODE48 → NODE256 as children are added.

### When to Use

- String-keyed maps (symbol tables, routing tables)
- IP prefix matching (routing, firewall rules)
- Database indexes (PostgreSQL trie indexes)
- Autocomplete / prefix search
- When keys share long common prefixes

---

## 7. Custom Structures

### 7.1 Intrusive Linked List

```c
// Node embedded in the containing struct — no separate allocation
typedef struct intr_node {
    struct intr_node *next;
    struct intr_node *prev;
} intr_node_t;

// Container embeds the node:
typedef struct {
    intr_node_t link;  // embedded, not a pointer
    uint64_t account_id;
    double balance;
    // ... other fields
} account_t;

// O(1) insert/remove with zero allocation
void intr_insert_after(intr_node_t *pos, intr_node_t *node) {
    node->next = pos->next;
    node->prev = pos;
    pos->next->prev = node;
    pos->next = node;
}
```

| Metric | Value |
|--------|-------|
| **Insert/remove** | ~5 ns |
| **Memory overhead** | 16 bytes per node (2 pointers) |
| **Cache efficiency** | Excellent — node is inside the object |
| **Allocation** | None (embedded) |

### 7.2 Memory Pool / Arena Allocator

```c
typedef struct {
    char *base;
    size_t used;
    size_t total;
    size_t alignment;
} arena_t;

// Bump allocator: O(1), ~3 ns
void *arena_alloc(arena_t *a, size_t size) {
    size = (size + a->alignment - 1) & ~(a->alignment - 1);
    if (a->used + size > a->total) return NULL;
    void *ptr = a->base + a->used;
    a->used += size;
    return ptr;
}

// Reset: O(1) — free everything at once
void arena_reset(arena_t *a) { a->used = 0; }
```

| Metric | Value |
|--------|-------|
| **Allocation** | ~3 ns (bump pointer) |
| **Deallocation** | O(1) (arena reset) |
| **Memory overhead** | 0 bytes per allocation |
| **Cache efficiency** | Perfect — sequential allocation = sequential memory |
| **Fragmentation** | None |

### 7.3 Slab Allocator

```c
// Fixed-size object allocator — no fragmentation, O(1) alloc/free
typedef struct slab {
    void *free_list;  // singly-linked list of free objects
    uint32_t obj_size;
    uint32_t objs_per_slab;
    uint32_t num_slabs;
} slab_t;

void *slab_alloc(slab_t *s) {
    if (!s->free_list) slab_grow(s);  // allocate new slab
    void *obj = s->free_list;
    s->free_list = *(void **)obj;  // pop from free list
    return obj;
}

void slab_free(slab_t *s, void *obj) {
    *(void **)obj = s->free_list;  // push to free list
    s->free_list = obj;
}
```

| Metric | Value |
|--------|-------|
| **Alloc/free** | ~5 ns |
| **Memory overhead** | 8 bytes per free object (next pointer) |
| **Cache efficiency** | Good — objects are same size, good spatial locality |
| **Fragmentation** | None (fixed-size) |

### 7.4 Hashed Array Tree (HAT)

```c
// Two-level structure: top directory + leaf fragments
// O(1) append, O(1) random access, amortized O(1) growth
// No reallocation of existing data (unlike std::vector)

#define LEAF_SIZE 1024

typedef struct {
    void **directory;     // array of leaf pointers
    uint32_t top_size;    // number of leaves
    uint32_t count;       // total elements
} hat_t;

void *hat_get(hat_t *h, uint32_t idx) {
    uint32_t leaf = idx / LEAF_SIZE;
    uint32_t offset = idx % LEAF_SIZE;
    return h->directory[leaf][offset];
}

// Append: O(1) amortized, only allocates new leaf when current is full
void hat_append(hat_t *h, void *item) {
    uint32_t leaf = h->count / LEAF_SIZE;
    uint32_t offset = h->count % LEAF_SIZE;
    if (offset == 0) h->directory[leaf] = malloc(LEAF_SIZE * sizeof(void*));
    h->directory[leaf][offset] = item;
    h->count++;
}
```

| Metric | Value |
|--------|-------|
| **Random access** | ~3 ns (2 pointer dereferences) |
| **Append** | ~5 ns amortized |
| **Memory overhead** | 8 bytes per 1024 elements (directory) |
| **Cache efficiency** | Good — leaves are contiguous |
| **Growth cost** | No copy of existing data |

### 7.5 Lock-Free Stack (Treiber Stack)

```c
typedef struct lf_node {
    void *value;
    struct lf_node *next;
} lf_node_t;

typedef struct {
    _Atomic(lf_node_t *) head;
} lf_stack_t;

void lf_push(lf_stack_t *s, lf_node_t *node) {
    lf_node_t *old_head;
    do {
        old_head = atomic_load_explicit(&s->head, memory_order_relaxed);
        node->next = old_head;
    } while (!atomic_compare_exchange_weak_explicit(
        &s->head, &old_head, node,
        memory_order_release, memory_order_relaxed));
}

lf_node_t *lf_pop(lf_stack_t *s) {
    lf_node_t *old_head;
    do {
        old_head = atomic_load_explicit(&s->head, memory_order_acquire);
        if (!old_head) return NULL;
    } while (!atomic_compare_exchange_weak_explicit(
        &s->head, &old_head, old_head->next,
        memory_order_acquire, memory_order_relaxed));
    return old_head;
}
```

| Metric | Value |
|--------|-------|
| **Push/pop** | ~20–40 ns (CAS contention) |
| **Memory overhead** | 8 bytes per node (next pointer) |
| **ABA problem** | Requires tagged pointers or hazard pointers |
| **Cache lines** | 1 (head) + 1 (node) |

### 7.6 Hazard Pointer (Safe Memory Reclamation)

```c
// Solves ABA and use-after-free in lock-free structures
#define MAX_HAZARDS 4
#define MAX_THREADS 64

typedef struct {
    _Atomic(void *) hazard[MAX_THREADS][MAX_HAZARDS];
    // Retired list per thread
    struct retired_node *retired[MAX_THREADS];
} hp_record_t;

// Thread announces what it's accessing
void hp_set(hp_record_t *hp, int tid, int slot, void *ptr) {
    atomic_store_explicit(&hp->hazard[tid][slot], ptr, memory_order_release);
}

// Thread retires a node (deferred free)
void hp_retire(hp_record_t *hp, int tid, void *ptr) {
    // Add to retired list, scan when list is long
    // Free only when no hazard pointer references it
}
```

| Metric | Value |
|--------|-------|
| **Protection cost** | ~2 ns per pointer access |
| **Reclamation** | Batched, amortized |
| **Memory overhead** | 4 pointers per thread |
| **Cache efficiency** | Good — hazard array is small and hot |

---

## 8. Selection Guide

### By Access Pattern

| Pattern | Best Structure | Latency | Why |
|---------|---------------|---------|-----|
| FIFO queue (1:1) | SPSC Ring Buffer | ~5 ns | Zero contention, 1 cache line |
| FIFO queue (N:1) | MPSC Ring Buffer | ~25 ns | Single consumer, CAS on head |
| FIFO queue (N:N) | MPMC Ring Buffer (Vyukov) | ~50 ns | Per-cell sequencing |
| Key-value lookup | SwissTable Hash Map | ~4 ns | SIMD probing, 1 cache line |
| Ordered map (small) | B-Tree (B=16) | ~60 ns | 5 cache lines for 1M entries |
| Ordered map (large) | B+ Tree | ~50 ns | Linked leaves for range scans |
| String keys | ART Radix Tree | ~30 ns | Path compression, adaptive nodes |
| Sliding window | Circular Array | ~3 ns | No allocation, perfect prefetch |
| Lock-free stack | Treiber Stack | ~30 ns | Simple CAS, ABA-safe with HP |
| Memory allocation | Arena / Slab | ~3–5 ns | O(1), zero fragmentation |

### By Data Size

| Size | Recommended | Rationale |
|------|-------------|-----------|
| < 100 entries | Linear scan array | Beats any structure (cache-resident) |
| 100–10K | SwissTable / B-Tree | Fits in L2, SIMD probing wins |
| 10K–1M | B-Tree / ART | Minimize cache misses per lookup |
| 1M–100M | B+ Tree / ART | Disk-friendly, range queries |
| > 100M | B+ Tree / LSM-Tree | Disk-based, write-optimized |

### By Concurrency

| Threads | Pattern | Structure |
|---------|---------|-----------|
| 1 | Single-threaded | Any (no synchronization) |
| 2–8 | Sharded | Shard by key hash, one structure per shard |
| 8–64 | SPSC chains | Pipeline: SPSC ring between each stage |
| 64+ | MPMC + work stealing | Vyukov queue + per-thread deques |

### Cache Hierarchy Awareness

```
L1 cache:  32 KB,  ~4 cycles  →  SwissTable group, B-tree node (small)
L2 cache:  256 KB, ~12 cycles →  B-tree node (large), ART node4/16
L3 cache:  8 MB,   ~40 cycles →  Hash map (1M entries), skip list level 0
Main mem:  GB+,    ~100 cycles →  B+ tree internal nodes, ART node256
```

**Rule of thumb**: Structure your data so the hot path touches ≤ 3 cache lines per operation.

---

## Summary Table

| Structure | Latency | Throughput | Memory/Entry | Cache Lines/Op | Best For |
|-----------|---------|------------|-------------|----------------|----------|
| SPSC Ring | ~5 ns | ~200M/s | 8 B | 1 | 1:1 queues |
| MPMC Ring | ~50 ns | ~20M/s | 16 B | 2–4 | N:N queues |
| Circular Array | ~3 ns | ~300M/s | 8 B | 1 | Sliding windows |
| SwissTable | ~4 ns | ~250M/s | 9 B | 1 | General KV |
| Robin Hood | ~5 ns | ~200M/s | 18 B | 1–2 | Predictable worst-case |
| Skip List | ~100 ns | ~10M/s | 32 B | 20+ | Concurrent ordered |
| B-Tree (B=16) | ~60 ns | ~15M/s | 32 B | 5 | Large ordered |
| B+ Tree | ~50 ns | ~20M/s | 24 B | 3–4 | Range queries |
| ART Radix | ~30 ns | ~30M/s | 15 B | 1–3 | String keys |
| Intrusive List | ~5 ns | ~200M/s | 16 B | 1 | Embedded nodes |
| Arena Alloc | ~3 ns | ~300M/s | 0 B | 0 | Bulk allocation |
| Slab Alloc | ~5 ns | ~200M/s | 8 B | 1 | Fixed-size objects |
| HAT | ~3 ns | ~300M/s | ~0 B | 2 | Append-heavy arrays |
| Treiber Stack | ~30 ns | ~25M/s | 8 B | 2 | Lock-free LIFO |

---

*Last updated: 2026-09-29*
