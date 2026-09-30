#include "queue.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>

#define N 20000
#define P 4
static mpmc_queue_t queue;
static mpsc_queue_t many_producers;
static spmc_queue_t many_consumers;
static unsigned topology, target;
static bool push_item(void *item) {
    if (topology==1) return mpsc_push(&many_producers,item);
    if (topology==2) return spmc_push(&many_consumers,item);
    return mpmc_push(&queue,item);
}
static bool pop_item(void **item) {
    if (topology==1) return mpsc_pop(&many_producers,item);
    if (topology==2) return spmc_pop(&many_consumers,item);
    return mpmc_pop(&queue,item);
}
static _Atomic unsigned seen[P * N];
static _Atomic unsigned completed;
static unsigned payload[P * N];
static void *producer(void *arg) {
    unsigned producer_id = *(unsigned *)arg;
    for (unsigned i = 0; i < N; ++i) {
        unsigned id = producer_id * N + i;
        payload[id] = id;
        while (!push_item(&payload[id])) sched_yield();
    }
    return NULL;
}
static void *consumer(void *unused) {
    (void)unused;
    while (atomic_load(&completed) < target) {
        void *item;
        if (!pop_item(&item)) { sched_yield(); continue; }
        unsigned id = *(unsigned *)item;
        assert(id < P * N);
        assert(atomic_fetch_add(&seen[id], 1) == 0);
        atomic_fetch_add(&completed, 1);
    }
    return NULL;
}
int main(void) {
    spsc_queue_t spsc;
    assert(spsc_init(&spsc, 16) == 0);
    for (unsigned i = 0; i < 16; ++i) assert(spsc_push(&spsc, &payload[i]));
    assert(spsc_is_full(&spsc)); assert(!spsc_push(&spsc, payload));
    for (unsigned i = 0; i < 16; ++i) { void *p; assert(spsc_pop(&spsc, &p)); assert(p == &payload[i]); }
    spsc_destroy(&spsc);
    for(topology=0;topology<3;++topology) {
        unsigned producers_count=topology==2?1:P, consumers_count=topology==1?1:P;
        target=producers_count*N;atomic_store(&completed,0);
        for(unsigned i=0;i<P*N;++i) atomic_store(&seen[i],0);
        if(topology==0) assert(mpmc_init(&queue,16)==0);
        if(topology==1) assert(mpsc_init(&many_producers,16)==0);
        if(topology==2) assert(spmc_init(&many_consumers,16)==0);
        pthread_t producers[P],consumers[P];unsigned ids[P];
        for(unsigned i=0;i<producers_count;++i) { ids[i]=i;assert(pthread_create(&producers[i],NULL,producer,&ids[i])==0); }
        for(unsigned i=0;i<consumers_count;++i) assert(pthread_create(&consumers[i],NULL,consumer,NULL)==0);
        for(unsigned i=0;i<producers_count;++i) pthread_join(producers[i],NULL);
        for(unsigned i=0;i<consumers_count;++i) pthread_join(consumers[i],NULL);
        for(unsigned i=0;i<target;++i) assert(atomic_load(&seen[i])==1);
        if(topology==0) {assert(mpmc_is_empty(&queue));mpmc_destroy(&queue);}
        if(topology==1) {assert(mpsc_is_empty(&many_producers));mpsc_destroy(&many_producers);}
        if(topology==2) {assert(spmc_is_empty(&many_consumers));spmc_destroy(&many_consumers);}
    }
    disruptor_t disruptor; assert(disruptor_init(&disruptor, 16) == -1);
    ull_queue_t hybrid; assert(ull_queue_init(&hybrid, 16) == 0);
    for (unsigned i = 0; i < 16; ++i) assert(ull_queue_push(&hybrid, &payload[i]));
    ull_queue_set_mode(&hybrid, 1); assert(hybrid.mode == 0);
    for (unsigned i = 0; i < 16; ++i) { void *p; assert(ull_queue_pop(&hybrid, &p)); assert(p == &payload[i]); }
    ull_queue_destroy(&hybrid);
    puts("queue correctness: capacity, MPMC 4P/4C, MPSC 4P/1C and SPMC 1P/4C exact-once payloads, mode guard and unsupported barrier passed");
    return 0;
}
