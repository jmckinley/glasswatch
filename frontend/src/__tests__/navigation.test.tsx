/**
 * Navigation component tests
 * Tests nav link presence, active state, and "AI Assistant" label.
 */
import React from 'react'
import { render, screen } from '@testing-library/react'

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  usePathname: () => '/',
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('next/link', () => {
  return function Link({ children, href, className, title }: {
    children: React.ReactNode
    href: string
    className?: string
    title?: string
  }) {
    return <a href={href} className={className} title={title}>{children}</a>
  }
})

// Mock NotificationBell to avoid its API calls and auth context
jest.mock('@/components/notifications/NotificationBell', () => {
  return function NotificationBell() {
    return <div data-testid="notification-bell" />
  }
})

import Navigation from '@/components/Navigation'

describe('Navigation', () => {
  it('renders "AI Assistant" in the nav (not "AI Analyst" or "Agent")', () => {
    render(<Navigation />)
    expect(screen.getByText('AI Assistant')).toBeInTheDocument()
    expect(screen.queryByText('AI Analyst')).not.toBeInTheDocument()
    expect(screen.queryByText('Agent')).not.toBeInTheDocument()
  })

  it('renders all expected nav items', () => {
    render(<Navigation />)
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Vulnerabilities').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Bundles').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Compliance').length).toBeGreaterThan(0)
    expect(screen.getAllByText('AI Assistant').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Settings').length).toBeGreaterThan(0)
  })

  it('active link (Dashboard at "/") gets indigo styling', () => {
    render(<Navigation />)
    // The Dashboard link "/" is active when pathname is "/"
    const dashboardLinks = screen.getAllByRole('link', { name: /dashboard/i })
    const activeLink = dashboardLinks.find(el => el.className?.includes('indigo'))
    expect(activeLink).toBeTruthy()
  })

  it('non-active links do not get indigo active class', () => {
    render(<Navigation />)
    const vulnLinks = screen.getAllByRole('link', { name: /vulnerabilities/i })
    // When pathname is "/", vulnerabilities link should NOT be active
    const vulnLink = vulnLinks.find(el => el.getAttribute('href') === '/vulnerabilities')
    expect(vulnLink?.className).not.toContain('bg-indigo-700')
  })
})
