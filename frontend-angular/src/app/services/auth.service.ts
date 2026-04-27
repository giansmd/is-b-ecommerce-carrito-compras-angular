import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { map, Observable } from "rxjs";

export type UserRole = "cliente" | "admin";

export interface AuthSession {
  accessToken: string;
  role: UserRole;
  email: string;
  userId: number;
}

@Injectable({ providedIn: "root" })
export class AuthService {
  private readonly storageKey = "session";

  constructor(private http: HttpClient) {}

  get backendUrl(): string {
    return (window as any).env?.BACKEND_URL || "http://localhost:8000";
  }

  get session(): AuthSession | null {
    const raw = localStorage.getItem(this.storageKey);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AuthSession;
    } catch {
      return null;
    }
  }

  login(email: string, password: string): Observable<AuthSession> {
    return this.http
      .post<{ access_token: string; role: UserRole }>(`${this.backendUrl}/api/auth/login`, {
        email,
        password,
      })
      .pipe(
        map((res) => {
          const userId = this.extractUserIdFromJwt(res.access_token);
          const session: AuthSession = {
            accessToken: res.access_token,
            role: res.role,
            email,
            userId,
          };
          localStorage.setItem(this.storageKey, JSON.stringify(session));
          return session;
        }),
      );
  }

  logout(): void {
    localStorage.removeItem(this.storageKey);
  }

  private extractUserIdFromJwt(token: string): number {
    const payload = this.parseJwtPayload(token);
    const raw = payload?.user_id;
    const parsed = typeof raw === "number" ? raw : Number(raw);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private parseJwtPayload(token: string): any {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    try {
      const json = atob(padded);
      return JSON.parse(json);
    } catch {
      return null;
    }
  }
}
