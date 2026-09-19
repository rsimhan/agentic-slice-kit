# Concept Invariants: Deadlocks & Coffman Conditions

**Course:** CS8492 Operating Systems (Lecture 18)  
**Department:** Computer Science and Engineering, CEG Anna University  

---

## 1. Ground Truth Invariants

### Invariant 1: The Four Coffman Conditions
- A deadlock can occur **if and only if all four** of the following conditions hold simultaneously:
  1. **Mutual Exclusion:** At least one resource must be non-shareable.
  2. **Hold and Wait:** A process holds at least one resource and requests additional resources held by other processes.
  3. **No Preemption:** Resources cannot be forcibly confiscated from a process holding them.
  4. **Circular Wait:** A closed chain of processes exists, where each process holds at least one resource needed by the next.
- Breaking or preventing **any single one** of these four conditions guarantees that deadlock cannot occur.

### Invariant 2: Deadlock vs. Starvation
- **Deadlock:** A set of processes is permanently blocked waiting for an event (resource release) that only another process in the set can cause. Zero progress is possible for all deadlocked processes without external termination.
- **Starvation (Indefinite Blocking):** A process waits indefinitely because other processes repeatedly get prioritized. Progress is still fundamentally possible under a fair scheduling policy without terminating any process.

### Invariant 3: Safe State vs. Deadlocked State
- An **unsafe state** is **not** necessarily deadlocked. An unsafe state merely means the system cannot guarantee that all processes will finish under worst-case future requests.
- Deadlock is a strict subset of unsafe states. All deadlocked states are unsafe, but not all unsafe states are deadlocked.

---

## 2. Common Fallacy Patterns (Known Misconceptions)

### `CIRCULAR_WAIT_ALONE_IS_DEADLOCK`
- **Description:** Student asserts that having a cycle in a resource graph alone guarantees deadlock without verifying single-unit resources or mutual exclusion.
- **Example flawed claim:** *"If there is a cycle in the resource allocation graph, the system is deadlocked."*
- **Pedagogical counter:** In multiple-instance resource systems, a cycle is a necessary condition, not a sufficient condition.

### `STARVATION_EQUALS_DEADLOCK`
- **Description:** Conflating high contention / low priority starvation with deadlock.
- **Example flawed claim:** *"When a process waits too long in the queue and never gets the CPU, it is deadlocked."*
- **Pedagogical counter:** Starvation is a scheduling unfairness issue; deadlock is an unresolvable circular dependency.

### `UNSAFE_EQUALS_DEADLOCKED`
- **Description:** Believing an unsafe state in Banker's Algorithm means processes are currently halted in deadlock.
- **Example flawed claim:** *"If the system enters an unsafe state, a deadlock has occurred."*
- **Pedagogical counter:** Unsafe simply means safety cannot be guaranteed if all processes suddenly claim their maximum declared needs.
