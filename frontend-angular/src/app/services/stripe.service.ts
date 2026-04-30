import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { AuthService } from "./auth.service";

@Injectable({ providedIn: "root" })
export class StripeService {
  constructor(
    private http: HttpClient,
    private auth: AuthService,
  ) {}

  get backendBaseUrl(): string {
    return this.auth.backendUrl;
  }

  createCheckoutSession(payload: any): Observable<any> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.post<any>(
      `${this.backendBaseUrl}/api/payments/create-checkout-session`,
      payload,
      { headers },
    );
  }

  // Optional: backend may expose endpoints to confirm or query session
  getCheckoutSession(sessionId: string): Observable<any> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.get<any>(
      `${this.backendBaseUrl}/api/payments/session/${sessionId}`,
      { headers },
    );
  }
}
