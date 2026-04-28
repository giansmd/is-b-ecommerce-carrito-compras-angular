import { Component, OnInit } from "@angular/core";
import { Router } from "@angular/router";
import { AuthService, AuthSession } from "../services/auth.service";
import { CartService } from "../services/cart.service";
import { Product, ProductService } from "../services/product.service";

@Component({
  selector: "app-store",
  templateUrl: "./store.component.html",
  styleUrls: ["./store.component.css"],
})
export class StoreComponent implements OnInit {
  products: Product[] = [];
  cart: CartItem[] = [];
  requestedQuantities: Record<number, number> = {};
  session: AuthSession | null = null;
  email = "";
  password = "";
  isLoggedIn = false;
  reportStartDate = "";
  reportEndDate = "";
  isAdmin = false;
  showProductForm = false;
  editingProduct: Product | null = null;
  productForm = {
    name: "",
    description: "",
    price: 0,
    category: "",
    stock: 0,
    image_url: "",
  };

  get cartItemsCount(): number {
    return this.cart.reduce((sum, item) => sum + item.quantity, 0);
  }

  get cartTotal(): number {
    return this.cart.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  }

  get productImagePreviewUrl(): string {
    return this.productForm.image_url.trim();
  }

  constructor(
    private auth: AuthService,
    private productsApi: ProductService,
    private cartApi: CartService,
    private router: Router,
  ) {}

  ngOnInit() {
    this.loadProducts();
    this.checkSession();
    const today = new Date();
    const end = today.toISOString().slice(0, 10);
    const start = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    this.reportStartDate = start;
    this.reportEndDate = end;
  }

  checkSession() {
    const session = this.auth.session;
    if (!session) return;
    this.session = session;
    this.isLoggedIn = true;
    this.email = session.email;
    this.isAdmin = session.role === "admin";
  }

  loadProducts() {
    this.productsApi.list().subscribe((res) => {
      this.products = res;
      this.syncCartWithCurrentStock();
    });
  }

  login() {
    this.auth.login(this.email, this.password).subscribe({
      next: (session) => {
        this.session = session;
        this.isLoggedIn = true;
        this.isAdmin = session.role === "admin";
        this.loadProducts();
      },
      error: () => alert("Error de login"),
    });
  }

  logout() {
    this.auth.logout();
    this.session = null;
    this.isLoggedIn = false;
    this.isAdmin = false;
    this.cart = [];
    this.requestedQuantities = {};
    this.router.navigateByUrl("/");
  }

  openAdminOrders() {
    this.router.navigateByUrl("/admin/pedidos");
  }

  openAddProduct() {
    this.editingProduct = null;
    this.productForm = {
      name: "",
      description: "",
      price: 0,
      category: "",
      stock: 0,
      image_url: "",
    };
    this.showProductForm = true;
  }

  openEditProduct(product: Product) {
    this.editingProduct = product;
    this.productForm = {
      name: product.name,
      description: product.description || "",
      price: Number(product.price),
      category: product.category || "",
      stock: product.stock,
      image_url: product.image_url || "",
    };
    this.showProductForm = true;
  }

  saveProduct() {
    const request = this.editingProduct
      ? this.productsApi.update(this.editingProduct.id, this.productForm)
      : this.productsApi.create(this.productForm);
    request.subscribe({
      next: () => {
        this.loadProducts();
        this.showProductForm = false;
        alert(this.editingProduct ? "Producto actualizado" : "Producto creado");
      },
      error: () => alert(this.editingProduct ? "Error al actualizar producto" : "Error al crear producto"),
    });
  }

  deleteProduct(id: number) {
    if (!confirm("¿Estás seguro de eliminar este producto?")) return;
    this.productsApi.delete(id).subscribe({
      next: () => {
        this.loadProducts();
        alert("Producto eliminado");
      },
      error: () => alert("Error al eliminar producto"),
    });
  }

  addToCart(product: Product) {
    if (!this.isLoggedIn) return alert("Debes iniciar sesión");
    if (this.isAdmin) return alert("Solo usuarios cliente pueden agregar productos al carrito");

    const desiredQuantity = this.getRequestedQuantity(product.id);
    const availableStock = this.getAvailableStockForCart(product.id);
    if (availableStock <= 0) return alert("No hay stock disponible para agregar más unidades");

    if (desiredQuantity > availableStock) {
      this.requestedQuantities[product.id] = availableStock;
      return alert(`Solo hay ${availableStock} unidad(es) disponibles para este producto`);
    }

    this.cartApi.addToCart(product.id, desiredQuantity).subscribe({
      next: () => {
        const existing = this.cart.find((item) => item.productId === product.id);
        if (existing) {
          existing.quantity += desiredQuantity;
          existing.maxStock = product.stock;
        } else {
          this.cart.push({
            productId: product.id,
            name: product.name,
            unitPrice: Number(product.price),
            quantity: desiredQuantity,
            maxStock: product.stock,
          });
        }
        const newAvailableStock = this.getAvailableStockForCart(product.id);
        this.requestedQuantities[product.id] = newAvailableStock > 0 ? Math.min(desiredQuantity, newAvailableStock) : 1;
        alert("Producto agregado al carrito");
      },
      error: (error) => {
        if (error?.status === 400) {
          alert("Stock insuficiente. Se actualizará el stock disponible.");
          this.loadProducts();
          return;
        }
        alert("No se pudo agregar al carrito");
      },
    });
  }

  checkout() {
    if (!this.validateCartAgainstStock()) return;
    this.cartApi.checkout().subscribe({
      next: (res) => {
        this.cart = [];
        this.requestedQuantities = {};
        this.loadProducts();
        alert(`Compra realizada. Pedido #${res.order_id}. Total: ${res.total}`);
      },
      error: () => alert("No se pudo procesar el checkout"),
    });
  }

  getRequestedQuantity(productId: number): number {
    const current = this.requestedQuantities[productId];
    if (!current || current < 1) {
      this.requestedQuantities[productId] = 1;
      return 1;
    }
    return current;
  }

  setRequestedQuantity(product: Product, rawValue: number | string): void {
    const parsed = Number(rawValue);
    const safeValue = Number.isFinite(parsed) ? Math.floor(parsed) : 1;
    const max = Math.max(1, this.getAvailableStockForCart(product.id));
    this.requestedQuantities[product.id] = Math.min(Math.max(safeValue, 1), max);
  }

  increaseRequestedQuantity(product: Product): void {
    this.setRequestedQuantity(product, this.getRequestedQuantity(product.id) + 1);
  }

  decreaseRequestedQuantity(product: Product): void {
    this.setRequestedQuantity(product, this.getRequestedQuantity(product.id) - 1);
  }

  getAvailableStockForCart(productId: number): number {
    const product = this.products.find((p) => p.id === productId);
    if (!product) return 0;
    const alreadyInCart = this.getCartQuantity(productId);
    return Math.max(product.stock - alreadyInCart, 0);
  }

  hasStockAvailableForCart(productId: number): boolean {
    return this.getAvailableStockForCart(productId) > 0;
  }

  generateOperationalReport() {
    this.cartApi.generateOperationalReport(this.reportStartDate, this.reportEndDate).subscribe({
      next: (res) => this.openPdf(res.pdf_url),
      error: () => alert("No se pudo generar el reporte operacional"),
    });
  }

  generateManagementReport() {
    this.cartApi.generateManagementReport().subscribe({
      next: (res) => this.openPdf(res.pdf_url),
      error: () => alert("No se pudo generar el reporte gerencial"),
    });
  }

  private getCartQuantity(productId: number): number {
    const item = this.cart.find((cartItem) => cartItem.productId === productId);
    return item ? item.quantity : 0;
  }

  private syncCartWithCurrentStock(): void {
    this.cart = this.cart.filter((item) => {
      const product = this.products.find((p) => p.id === item.productId);
      if (!product || product.stock <= 0) return false;
      item.maxStock = product.stock;
      if (item.quantity > product.stock) item.quantity = product.stock;
      return item.quantity > 0;
    });

    this.products.forEach((product) => {
      const available = this.getAvailableStockForCart(product.id);
      const currentDesired = this.getRequestedQuantity(product.id);
      this.requestedQuantities[product.id] = available > 0 ? Math.min(currentDesired, available) : 1;
    });
  }

  private validateCartAgainstStock(): boolean {
    for (const item of this.cart) {
      const product = this.products.find((p) => p.id === item.productId);
      if (!product) {
        alert(`El producto ${item.name} ya no está disponible.`);
        this.syncCartWithCurrentStock();
        return false;
      }
      if (item.quantity > product.stock) {
        alert(`Stock insuficiente para ${item.name}. Máximo disponible: ${product.stock}.`);
        this.syncCartWithCurrentStock();
        return false;
      }
    }
    return true;
  }

  private openPdf(pdfUrl: string) {
    const absolute = `${this.auth.backendUrl}${pdfUrl}`;
    window.open(absolute, "_blank");
  }
}

interface CartItem {
  productId: number;
  name: string;
  unitPrice: number;
  quantity: number;
  maxStock: number;
}
