'use client';

import { create } from 'zustand';

interface UIState {
  // Sidebar
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebarCollapsed: () => void;

  // Mobile menu
  mobileMenuOpen: boolean;
  isMobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  toggleMobileMenu: () => void;
  closeMobileMenu: () => void;

  // Command palette
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // Create menu
  createMenuOpen: boolean;
  setCreateMenuOpen: (open: boolean) => void;

  // Generic modal
  activeModal: string | null;
  modalData: Record<string, unknown> | null;
  openModal: (modalId: string, data?: Record<string, unknown>) => void;
  closeModal: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Sidebar state
  sidebarOpen: true,
  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  // Mobile menu state
  mobileMenuOpen: false,
  isMobileMenuOpen: false,
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open, isMobileMenuOpen: open }),
  toggleMobileMenu: () => set((state) => ({
    mobileMenuOpen: !state.mobileMenuOpen,
    isMobileMenuOpen: !state.isMobileMenuOpen
  })),
  closeMobileMenu: () => set({ mobileMenuOpen: false, isMobileMenuOpen: false }),

  // Command palette state
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  // Create menu state
  createMenuOpen: false,
  setCreateMenuOpen: (open) => set({ createMenuOpen: open }),

  // Modal state
  activeModal: null,
  modalData: null,
  openModal: (modalId, data = {}) => set({ activeModal: modalId, modalData: data }),
  closeModal: () => set({ activeModal: null, modalData: null }),
}));

// Selector hooks
export const useSidebarOpen = () => useUIStore((state) => state.sidebarOpen);
export const useSidebarCollapsed = () => useUIStore((state) => state.sidebarCollapsed);
export const useMobileMenuOpen = () => useUIStore((state) => state.mobileMenuOpen);
