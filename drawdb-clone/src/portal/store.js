import { create } from 'zustand';

/**
 * Portal state.
 *   role:    null | 'teacher' | 'student'
 *   view:    'home' | 'editor'
 *   mode:    null (free drawing) | 'author' (teacher creating a question)
 *            | 'review' (teacher inspecting a question's reference)
 *            | 'solve' (student answering a question)
 *   question: the active question ({id, title, prompt}) for review/solve
 */
export const usePortal = create((set) => ({
  role: localStorage.getItem('er-portal-role') || null,
  view: 'home',
  mode: null,
  question: null,
  result: null,
  set,
  setRole(role) {
    try {
      if (role) localStorage.setItem('er-portal-role', role);
      else localStorage.removeItem('er-portal-role');
    } catch (e) {}
    set({ role, view: 'home', mode: null, question: null, result: null });
  },
  backToPortal() {
    set({ view: 'home', mode: null, question: null, result: null });
  },
}));
