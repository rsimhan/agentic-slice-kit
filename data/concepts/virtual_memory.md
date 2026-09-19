# Concept Invariants: Virtual Memory & Page Table Address Translation

**Course:** CS8492 Operating Systems (Lecture 14)  
**Department:** Computer Science and Engineering, CEG Anna University  

---

## 1. Ground Truth Invariants

### Invariant 1: TLB Miss vs. Page Fault (Memory vs. Disk)
- A **TLB miss** is resolved purely in **physical RAM** by traversing the Page Table. It does **not** trigger disk I/O.
- Disk I/O occurs **only** when the Page Table entry has its **Valid/Present bit set to 0** (a **Page Fault** software interrupt handled by the OS kernel).
- Therefore, a TLB miss only causes disk access if the requested page is also absent from physical memory. A page can be present in RAM while missing from the TLB cache.

### Invariant 2: Address Translation & Bit Mapping
- The Virtual Address is partitioned into Virtual Page Number (VPN) and Offset bits: `[ VPN | Offset ]`.
- Address translation maps the **Virtual Page Number (VPN)** to a **Physical Frame Number (PFN)**.
- The **Offset bits remain completely unmodified** during translation because the page size equals the frame size.

### Invariant 3: Hardware vs. Software Execution Boundary
- Normal address translation on a TLB hit is executed entirely in **hardware by the Memory Management Unit (MMU)** at CPU clock speeds.
- A **Page Fault** transfers control to the **OS kernel trap handler (software)**, which suspends the process, issues disk I/O, updates the page table, and restarts the faulting instruction.

---

## 2. Common Fallacy Patterns (Known Misconceptions)

### `TLB_MISS_EQUALS_DISK_IO`
- **Description:** Student asserts that a TLB miss directly causes secondary storage (disk/swap) access or immediately triggers a page fault.
- **Example flawed claim:** *"If the address is not in the TLB, that's a page fault, so the OS reads the page from the hard drive."*
- **Pedagogical counter:** A page may be resident in RAM; the MMU walks the in-memory page table before any disk I/O is considered.

### `OFFSET_MODIFIED_DURING_TRANSLATION`
- **Description:** Student asserts that the offset bits change, get translated, or are recalculated during address translation.
- **Example flawed claim:** *"The MMU translates both the VPN and the offset to find the exact byte in memory."*
- **Pedagogical counter:** Page size matches frame size; offset is a relative distance from the base and passes through unaltered.

### `TLB_LOOKUP_IS_OS_SOFTWARE`
- **Description:** Student conflates hardware MMU operations with OS kernel intervention, claiming the operating system searches the TLB.
- **Example flawed claim:** *"The OS checks the TLB on every memory reference."*
- **Pedagogical counter:** The OS sets up page table registers, but TLB lookup is performed directly in hardware by the MMU on every instruction.

---

## 3. Scope Boundaries (Refusal Conditions)
- Out-of-scope topics: Disk Scheduling (SCAN, C-LOOK), CPU Scheduling (Round Robin, CFS), File System Inodes.
- If a student brings up out-of-scope topics, prompt them to refocus specifically on Virtual Memory Address Translation.
