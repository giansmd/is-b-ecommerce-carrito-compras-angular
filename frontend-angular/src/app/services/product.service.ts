import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { AuthService } from "./auth.service";

export interface Product {
  id: number;
  name: string;
  description?: string | null;
  price: string | number;
  category?: string | null;
  stock: number;
  image_url?: string | null;
}

export interface ProductCreate {
  name: string;
  description?: string | null;
  price: number;
  category?: string | null;
  stock: number;
  image_url?: string | null;
}

@Injectable({ providedIn: "root" })
export class ProductService {
  constructor(
    private http: HttpClient,
    private auth: AuthService,
  ) {}

  list(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.auth.backendUrl}/api/products`);
  }

  create(product: ProductCreate): Observable<Product> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.post<Product>(
      `${this.auth.backendUrl}/api/products`,
      product,
      { headers },
    );
  }

  update(id: number, product: Partial<ProductCreate>): Observable<Product> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.put<Product>(
      `${this.auth.backendUrl}/api/products/${id}`,
      product,
      { headers },
    );
  }

  delete(id: number): Observable<any> {
    const session = this.auth.session;
    const headers = session
      ? new HttpHeaders().set("Authorization", `Bearer ${session.accessToken}`)
      : undefined;
    return this.http.delete(`${this.auth.backendUrl}/api/products/${id}`, {
      headers,
    });
  }
}
