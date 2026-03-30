export const Role = {
  USER: "USER",
  VIP: "VIP",
  ADMIN: "ADMIN",
} as const;

export type Role = (typeof Role)[keyof typeof Role];

export const isRole = (value: string): value is Role =>
  Object.values(Role).includes(value as Role);